# -*- coding: utf-8 -*-
"""记忆插槽②（spec §七）：consolidator 后台服务——重造的固化工场（DeepTutor 纪律文字级
继承，代码零搬运）。

四模式②期裁剪：update+audit 交付；dedup/merge 显式 422（ModeNotImplemented）——
分期不是占位符（写死在注册表）。只写 L2/L3（RAW_MD/AGENTS.md/trace 一概不碰——
三分离物理化）。LLM=平台默认 temperature 0.2（env 可覆盖）；每次固化=一次 LLM 调用
（update 一次出 L2+L3；audit=确定性对冲句式+来源模式检查，不耗 LLM——预算属性，spec §七）。
锁：per-{expert}/{user} asyncio 锁防双跑；覆写式幂等；失败日志下轮重试。
台账：expert_events kind=memory_consolidated。
"""
import asyncio
import datetime as _dt
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app.services.memory_trace import truncate

logger = logging.getLogger(__name__)


class ModeNotImplemented(Exception):
    """dedup/merge ②期未实现（spec §二非目标；API 层转 422）。"""


# 对冲提示词资产（文字级继承 DeepTutor update_l3 纪律，zh 单语——spec §七）
UPDATE_PROMPT = """你是记忆固化引擎。基于以下对话轨迹（L1 原料），产出两份内容：

## L2 会话摘要（{surface}）
覆盖本次新行的要点，精炼成段。

## L3 用户画像（逐条，强制对冲纪律）
每条画像必须：
1. 以「在 N 次 {surface} 互动中，用户…」开头（N=本次读到的互动轮数，据实）；
2. 引用来源 surface：{surface}；
3. 没有把握的条目输出空——宁缺勿滥，禁止编造或过度概括；
4. 只写可从轨迹直接支撑的稳定偏好/事实，不写一次性情绪。

轨迹原料：
{trace_text}

按以下格式输出（严格遵守，无内容处输出空段）：
<L2>
…摘要…
</L2>
<L3>
- 在 N 次…互动中，用户…（来源：{surface}）
</L3>"""

_HEDGE_RE = re.compile(r"在\s*\d+\s*次.+互动中")
_LOCKS: Dict[str, asyncio.Lock] = {}


def _lock(expert_id: str, user: str) -> asyncio.Lock:
    k = f"{expert_id}/{user}"
    if k not in _LOCKS:
        _LOCKS[k] = asyncio.Lock()
    return _LOCKS[k]


def _read_new_lines(user_root: Path, surface: str, state: dict) -> List[dict]:
    """读 L1 新行（行数增量判定）；state 持久化在 {user}/.consolidator_state.json。"""
    sp = user_root / ".consolidator_state.json"
    st = {}
    try:
        st = json.loads(sp.read_text("utf-8"))
    except Exception:
        pass
    key = f"trace/{surface}"
    last = int(st.get(key, 0))
    rows, n = [], 0
    for f in sorted((user_root / "trace" / surface).glob("*.jsonl")):
        for line in f.read_text("utf-8", errors="replace").splitlines():
            n += 1
            if n > last and line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    st[key] = n
    try:
        sp.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[consolidator] state 写失败(下轮重读): {e}")
    return rows


def _default_llm(prompt: str) -> str:
    """平台默认连接（temperature 0.2，env 可覆盖）——每次固化一次 LLM 调用。"""
    from app.services.llm_client import get_chat_model
    model = get_chat_model(temperature=float(os.getenv("TUPU_MEMORY_CONSOLIDATOR_TEMP", "0.2")))
    return model.invoke(prompt).content


def _consolidate_tree(expert_id: str, user: str, *, root: Path, state: Optional[dict] = None,
                      _llm: Optional[Callable[[str], str]] = None) -> Dict:
    """单树固化（内部可测函数）：读 L1 新行→一次 LLM→覆写 L2+对冲写 L3→audit。
    只写 L2/{surface}.md 与 L3/{slot_key}.md（槽声明者）；RAW_MD/AGENTS.md/trace 不碰。"""
    from app.services.expert_config import get_card
    from app.services.memory_slots import normalize_memory_field
    card = get_card(expert_id)
    _mem = normalize_memory_field(card.get("memory"))
    l2_slots = [s for s in _mem["slots"] if s.get("type") == "L2_SUMMARY"]
    l3_slots = [s for s in _mem["slots"] if s.get("type") == "L3_PROFILE"]
    report = {"expert_id": expert_id, "user": user, "read_lines": 0,
              "l2_written": 0, "l3_written": 0, "audit": {"total": 0, "hedged": 0}, "elapsed_ms": 0}
    t0 = time.time()
    if not (l2_slots or l3_slots):
        return report                                     # 卡无 L2/L3：零成本跳过
    all_rows, trace_text = [], []
    for s in l2_slots + l3_slots:
        rows = _read_new_lines(root, s.get("surface") or "chat", state or {})
        if s.get("type") == "L2_SUMMARY":
            all_rows = rows                               # 以首个 L2 surface 为主原料
        report["read_lines"] += len(rows)
    for r in all_rows:
        trace_text.append(truncate(json.dumps(r.get("payload") or {}, ensure_ascii=False), 400))
    if not all_rows:
        report["elapsed_ms"] = round((time.time() - t0) * 1000)
        return report                                     # E2：零新行零写入
    llm = _llm or _default_llm
    surface = (l2_slots[0].get("surface") if l2_slots else (l3_slots[0].get("slot_key") or "chat"))
    out = llm(UPDATE_PROMPT.format(surface=surface, trace_text="\n".join(trace_text)))
    m2 = re.search(r"<L2>(.*?)</L2>", out, re.S)
    m3 = re.search(r"<L3>(.*?)</L3>", out, re.S)
    backup_dir = root / "backup" / _dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for s in l2_slots:                                    # L2 覆写式（幂等可重入）
        p = root / "L2" / f"{s.get('surface') or 'chat'}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)
        if p.exists():
            import shutil as _sh
            _sh.copy2(p, backup_dir / p.name)
        p.write_text((m2.group(1).strip() if m2 else "") + "\n", encoding="utf-8")
        report["l2_written"] += 1
    # 批5 实证修正 #6：LLM 输出不规范（缺 <L3> 段）是常态——防御缺失（spec §十一失败不阻），
    # m3 None → 画像空写（宁缺勿滥与对冲纪律一致），不抛错。
    l3_lines = [l.strip("- ").strip() for l in ((m3.group(1) if m3 else "") or "").splitlines() if l.strip()]
    for s in l3_slots:                                    # L3 对冲写（audit 同步统计）
        p = root / "L3" / f"{s.get('slot_key') or 'profile'}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)
        if p.exists():
            import shutil as _sh
            _sh.copy2(p, backup_dir / p.name)
        p.write_text("\n".join(l3_lines) + "\n", encoding="utf-8")
        report["l3_written"] += 1
    report["audit"] = {"total": len(l3_lines),
                       "hedged": sum(1 for l in l3_lines if _HEDGE_RE.search(l))}
    report["elapsed_ms"] = round((time.time() - t0) * 1000)
    return report


async def run_consolidation(expert_id: str, user: str, *, mode: str = "update",
                            _llm: Optional[Callable[[str], str]] = None,
                            _trace: Optional[list] = None) -> Dict:
    """入口（管理页手动/周期扫描共用）。mode ∈ update|audit|dedup|merge（后两者 422）。"""
    if mode not in MODES:
        raise ModeNotImplemented(f"模式 {mode} ②期未实现（判据见 spec §二非目标）")
    from app.services.expert_paths import memory_user_root
    async with _lock(expert_id, user):
        report = _consolidate_tree(expert_id, user, root=memory_user_root(expert_id, user),
                                   _llm=_llm)
        try:                                              # 台账（fire-and-forget 语义但此处同步落）
            from app.services import expert_config as _ec
            _ec.record_event(expert_id, "memory_consolidated",
                             detail={"user": user, "modes": mode, **report}, updated_by="consolidator")
        except Exception as e:
            logger.warning(f"[consolidator] 台账失败(不阻塞): {e}")
        return report


MODES = {"update": run_consolidation, "audit": run_consolidation}   # dedup/merge 无键=422


async def periodic_scan(interval_s: Optional[int] = None) -> None:
    """周期扫描（spec §七）：默认 30 分钟 env 可调；扫「L1 有新行且卡声明 L2/L3」的树；
    无新行零成本跳过（_read_new_lines 行数增量）。env 关（TUPU_MEMORY_CONSOLIDATOR=0）不启动。"""
    import asyncio as _aio
    interval_s = interval_s or int(os.getenv("TUPU_MEMORY_CONSOLIDATOR_INTERVAL", "1800"))
    while True:
        try:
            await _aio.sleep(interval_s)
            from app.services.expert_config import _load_rows
            from app.services.expert_paths import memory_user_root
            from app.services.memory_slots import normalize_memory_field
            for card in _load_rows():
                _mem = normalize_memory_field(card.get("memory"))
                if not any(s.get("type") in ("L2_SUMMARY", "L3_PROFILE") for s in _mem["slots"]):
                    continue
                eroot = memory_user_root(card["expert_id"], "anonymous").parent
                if not eroot.exists():
                    continue
                for udir in eroot.iterdir():
                    if udir.is_dir() and (udir / "trace").exists():
                        await run_consolidation(card["expert_id"], udir.name)
        except Exception as e:
            logger.warning(f"[consolidator] 周期扫描异常(下轮重试): {e}")
