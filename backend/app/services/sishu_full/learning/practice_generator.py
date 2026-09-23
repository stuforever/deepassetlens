"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request as _ur
from pathlib import Path
from typing import Any

from app.services.sishu_full.multi_user.paths import get_current_path_service

logger = logging.getLogger(__name__)

# 三档定义（与 KP difficulty 1-5 对齐）
TIERS = {"basic": "基础", "intermediate": "提高", "advanced": "挑战"}
TIER_ORDER = ["basic", "intermediate", "advanced"]
TIER_ANCHOR = {
    "basic": "单步直用公式或概念辨析，题干简短，选项干扰弱（对应知识点难度1-2）",
    "intermediate": "两步推理或两个知识点组合，需要转化条件（难度3）",
    "advanced": "多步综合、逆向求解或条件开放（难度4-5），可基于种子题出变式",
}

MAX_VERSIONS = 5
COOLDOWN_SECONDS = 60
DEFAULT_COUNT = 5

_SYSTEM_PROMPT = """你是一位资深数学教师。请根据给定的章节和知识点清单，生成对应难度档位的练习题。
要求：
- 题目必须围绕给定知识点，且每题标注其 kp_id（必须来自知识点清单）
- 选择题（type=choice）4 个选项，answer 为选项字母（A/B/C/D）
- 填空题（type=fill）无 options，answer 为标准答案文本
- 每道题标注 difficulty（1-5 整数，对应知识点难度）
- 只输出 JSON 数组，不要 markdown、不要任何解释
- 示例: [{"ask":"...","type":"choice","options":["A内容","B内容","C内容","D内容"],"answer":"A","kp_id":"...","difficulty":2}]"""


# --------------------------------------------------------------------------- #
# 缓存读写（用户工作区，随 user_context 自动 u 隔离）                           #
# --------------------------------------------------------------------------- #


def _cache_path(chapter_id: str) -> Path:
    # R5批⑯（清单安全）：chapter_id 来自 HTTP 入参，未校验即拼路径（'..'/'/' 可穿越
    # 用户工作区）。净化：仅允许字母数字下划线连字符（\w 含中文），其余拒绝。
    import re as _re

    if not isinstance(chapter_id, str) or not _re.fullmatch(r"[\w-]{1,128}", chapter_id):
        raise ValueError(f"非法 chapter_id: {chapter_id!r}")
    # 用户感知：user_context(h5_user_guarded(u)) 内返回该用户工作区（随 u 隔离）
    return get_current_path_service().get_workspace_dir() / "practice_gen" / f"{chapter_id}.json"


def load_practice_cache(chapter_id: str, tier: str) -> dict[str, Any]:
    """读该章节某档缓存题组；无则返回空 dict。"""
    if tier not in TIERS:
        tier = "basic"
    p = _cache_path(chapter_id)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data.get(tier) or {}


def _save_practice_cache(chapter_id: str, tier: str, entry: dict[str, Any]) -> None:
    p = _cache_path(chapter_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
    data[tier] = entry
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _all_generated_texts(chapter_id: str) -> list[str]:
    """读该章节全部档位已生成题文本（前 60 字去空白），作 LLM 排除清单。"""
    p = _cache_path(chapter_id)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    out: list[str] = []
    for entry in data.values():
        for ver in entry.get("versions") or []:
            for q in ver:
                txt = str(q.get("ask") or "")
                out.append(re.sub(r"\s+", "", txt)[:60])
    return out


def recommend_tier(chapter_id: str, u: str = "") -> str:
    """按该章节 KP 与画像交集推荐档位（设计 §四 PG-3）：

    - 本章有薄弱点 -> basic（夯基础）
    - 本章全部已掌握 -> advanced（挑战）
    - 否则 -> intermediate（提高）

    必须在 h5 用户上下文（或 admin 上下文）内调用，画像才指向正确用户。
    """
    try:
        from app.services.sishu_full.learning.curriculum import CurriculumStore
        from app.services.sishu_full.learning.learner_profile import build_learner_profile
        from app.services.sishu_full.multi_user.paths import local_admin_user, user_context

        with user_context(local_admin_user()):
            cs = CurriculumStore()
            chapter = next((c for c in cs.list_chapters("") if c.id == chapter_id), None)
            kp_ids = set(chapter.kp_ids or []) if chapter is not None else set()
        if not kp_ids:
            return "intermediate"
        profile = build_learner_profile(user_id=u or "default")
        weak = set(profile.weak_points or [])
        strong = set(profile.strong_points or [])
        if kp_ids & weak:
            return "basic"
        if kp_ids and kp_ids <= strong:
            return "advanced"
        return "intermediate"
    except Exception:  # noqa: BLE001
        return "intermediate"


def current_questions(chapter_id: str, tier: str) -> tuple[list[dict], int, int]:
    """返回 (当前版本题目, current_version, version_count)。"""
    entry = load_practice_cache(chapter_id, tier)
    versions = entry.get("versions") or []
    n = len(versions)
    cur = 0
    if n:
        try:
            cur = max(0, min(int(entry.get("current", 0)), n - 1))
        except (TypeError, ValueError):
            cur = 0
    return (versions[cur] if versions else []), cur, n


def rotate_version(chapter_id: str, tier: str) -> dict[str, Any]:
    """切到下一版本（轮换零成本，不调 LLM）。返回该档当前状态。"""
    entry = load_practice_cache(chapter_id, tier)
    versions = entry.get("versions") or []
    n = len(versions)
    cur = 0
    if n:
        try:
            cur = int(entry.get("current", 0))
        except (TypeError, ValueError):
            cur = 0
        cur = (cur + 1) % n
        entry["current"] = cur
        _save_practice_cache(chapter_id, tier, entry)
    questions = versions[cur] if versions else []
    return {"questions": questions, "version": cur, "version_count": n}


def cooldown_left(chapter_id: str, tier: str) -> int:
    """距下次可重新生成还剩的秒数（0 = 可生成）。"""
    entry = load_practice_cache(chapter_id, tier)
    last = entry.get("last_generated_at") or 0
    try:
        last = float(last)
    except (TypeError, ValueError):
        last = 0
    remain = int(COOLDOWN_SECONDS - (time.time() - last))
    return max(0, remain)


# --------------------------------------------------------------------------- #
# LLM 生成                                                                     #
# --------------------------------------------------------------------------- #


def _validate_items(items: Any, chapter, kp_by_id: dict[str, Any]) -> list[dict]:
    """校验：kp_id 必须在章节 kp_ids 内；choice 必有 options>=3 且 answer∈选项；fill answer 非空。"""
    ok_ids = set(chapter.kp_ids or [])
    out: list[dict] = []
    if not isinstance(items, list):
        return out
    letters = "ABCDEFGH"
    for it in items:
        if not isinstance(it, dict):
            continue
        ask = str(it.get("ask") or "").strip()
        if not ask:
            continue
        qtype = str(it.get("type") or "choice").lower()
        kid = str(it.get("kp_id") or "")
        if kid not in ok_ids:
            continue
        try:
            diff = int(it.get("difficulty", 1))
        except (TypeError, ValueError):
            diff = 1
        diff = max(1, min(5, diff))
        if qtype == "fill":
            ans = str(it.get("answer") or "").strip()
            if not ans:
                continue
            out.append({"ask": ask, "type": "fill", "answer": ans, "kp_id": kid, "difficulty": diff})
        else:
            options = it.get("options") or []
            if not isinstance(options, list):
                continue
            options = [str(o).strip() for o in options if isinstance(o, str) and str(o).strip()]
            if len(options) < 3:
                continue
            ans = str(it.get("answer") or "").strip().upper()
            if ans in letters[: len(options)]:
                pass
            elif ans.isdigit() and 0 <= int(ans) < len(options):
                ans = letters[int(ans)]
            else:
                idx = next(
                    (i for i, o in enumerate(options) if o == str(it.get("answer"))),
                    None,
                )
                if idx is None:
                    continue
                ans = letters[idx]
            out.append({
                "ask": ask,
                "type": "choice",
                "options": options,
                "answer": ans,
                "kp_id": kid,
                "difficulty": diff,
            })
    return out


def _dedupe_vs_existing(valid: list[dict], excludes: list[str]) -> list[dict]:
    """生成后双保险：与已生成题做归一化包含过滤（PG-5 排除清单防复读）。"""
    if not excludes or not valid:
        return valid
    out: list[dict] = []
    for q in valid:
        t = re.sub(r"\s+", "", q.get("ask") or "")
        if not t:
            continue
        if any((t[:20] in e) or (e[:20] in t) for e in excludes):
            continue
        out.append(q)
    return out


def _call_llm(user_msg: str, cfg, *, endpoint: str = "practice_generate", u: str = "") -> str:
    """直调 LLM 生成内容；成功/失败均记成本日志（运营基建，不经 UsageTracker）。"""
    import time as _time

    from app.services.sishu_full.learning.llm_cost_log import log_llm_call

    body = json.dumps({
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 2500,
        "temperature": 0.8,
    }).encode("utf-8")
    req = _ur.Request(
        cfg.base_url + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key},
        method="POST",
    )
    t0 = _time.time()
    try:
        resp = _ur.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage") or {}
        log_llm_call(
            endpoint,
            user=u,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            ok=True,
            latency_ms=int((_time.time() - t0) * 1000),
        )
        return content
    except Exception as e:  # noqa: BLE001
        log_llm_call(
            endpoint,
            user=u,
            ok=False,
            latency_ms=int((_time.time() - t0) * 1000),
            error=str(e)[:120],
        )
        raise


def generate_practice(
    chapter_id: str,
    tier: str,
    count: int,
    u: str = "",
    *,
    seed_mothers: list[dict] | None = None,
) -> dict[str, Any]:
    """LLM 按档位为章节生成练习题并落盘（必须在 h5 用户上下文内调用）。

    返回 {"set": [...], "version": n, "generated": n}。异常：RuntimeError（LLM 未配置/
    返回无合法题/章节不存在）。
    """
    from app.services.sishu_full.learning.curriculum import CurriculumStore
    from app.services.sishu_full.services.llm.config import get_llm_config

    tier = tier if tier in TIERS else "basic"
    count = max(1, min(int(count), 8))

    # 1) 内容上下文（章节/KP 为全局共享，须在 admin 上下文读）：
    from app.services.sishu_full.multi_user.paths import local_admin_user, user_context

    with user_context(local_admin_user()):
        cs = CurriculumStore()
        _chs = cs.list_chapters("")
        chapter = next((c for c in _chs if c.id == chapter_id), None)
        if chapter is None:
            raise ValueError("chapter not found")
        kp_by_id = {k.id: k for k in cs.list_kps()}
        kp_lines: list[str] = []
        for kid in chapter.kp_ids or []:
            k = kp_by_id.get(kid)
            name = k.name if k else kid
            diff = k.difficulty if k and k.difficulty else 1
            kp_lines.append(f"- {kid} {name}（难度{diff}）")
        if not kp_lines:
            kp_lines.append(f"- {chapter_id} {chapter.name}（难度1）")

    # 2) 用户上下文：已生成题排除清单
    excludes = _all_generated_texts(chapter_id)

    cfg = get_llm_config()
    if not cfg.api_key or cfg.api_key == "sk-placeholder":
        raise RuntimeError("LLM key 未配置")

    seed_block = ""
    if tier == "advanced" and seed_mothers:
        lines = []
        for m in seed_mothers[:3]:
            lines.append(
                f"- 题干：{str(m.get('question_text') or m.get('title') or '')[:120]}；"
                f"错因：{m.get('wrong_reason') or '未知'}"
            )
        if lines:
            seed_block = (
                "\n种子错题（参考下面错题各出 1 道同类变式，换数/换情境，考查同一薄弱点）：\n"
                + "\n".join(lines)
            )

    ex_block = ""
    if excludes:
        ex_block = "\n排除以下已出过的题（不要重复或高度相似）：\n- " + "\n- ".join(excludes[:20])

    user_msg = (
        f"章节：{chapter.name}\n"
        f"知识点清单（出题必须围绕，且每题标注 kp_id）：\n"
        + "\n".join(kp_lines)
        + f"\n要求：生成 {count} 道{TIERS[tier]}档练习题。{TIER_ANCHOR[tier]}"
        + "\n题型：选择题（type=choice，4 个选项）与填空题（type=fill）混合，选择:填空 ≈ 6:4。"
        + ex_block
        + seed_block
        + "\n只输出 JSON 数组："
        '\n[{"ask":"...","type":"choice","options":["A内容","B内容","C内容","D内容"],'
        '"answer":"A","kp_id":"...","difficulty":2}]'
        "\n（fill 题无 options；answer 为标准答案文本）"
    )

    # 3) LLM 直调 + 校验（最多补一轮重试）
    valid: list[dict] = []
    for attempt in range(2):
        try:
            content = _call_llm(user_msg, cfg, u=u)
        except Exception as e:  # noqa: BLE001
            if attempt == 1:
                raise RuntimeError(f"LLM 调用失败: {e}") from e
            continue
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if not match:
            continue
        try:
            items = json.loads(match.group())
        except Exception:  # noqa: BLE001
            items = []
        valid = _validate_items(items, chapter, kp_by_id)
        # PG-5 双保险：归一化包含过滤排除清单
        valid = _dedupe_vs_existing(valid, excludes)
        if valid:
            break
    if not valid:
        raise RuntimeError("LLM 返回无合法题目")

    # 4) 落盘追加版本 + 更新冷却
    entry = load_practice_cache(chapter_id, tier)
    versions = entry.get("versions") or []
    version = len(versions)
    versions.append(valid)
    if len(versions) > MAX_VERSIONS:
        versions = versions[-MAX_VERSIONS:]
    entry["versions"] = versions
    entry["current"] = len(versions) - 1
    entry["last_generated_at"] = time.time()
    entry["updated_at"] = time.time()
    _save_practice_cache(chapter_id, tier, entry)
    return {"set": valid, "version": len(versions) - 1, "generated": len(valid)}


__all__ = [
    "TIERS",
    "TIER_ORDER",
    "TIER_ANCHOR",
    "MAX_VERSIONS",
    "COOLDOWN_SECONDS",
    "DEFAULT_COUNT",
    "load_practice_cache",
    "current_questions",
    "rotate_version",
    "cooldown_left",
    "recommend_tier",
    "generate_practice",
]
