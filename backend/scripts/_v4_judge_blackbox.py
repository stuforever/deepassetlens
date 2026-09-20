# -*- coding: utf-8 -*-
"""v4 协议 D：判分黑盒基线录制/重放（批0 录制→批3 重写后重放 diff）。
样本 ≥20 例×四态（对/半对/错/空）×题型（选择/填空/简答/计算/多选/判断+图片 2 例）。
经当前桥 POST /api/v2/skills/capability（skill_code=tutor/quiz，config.action=judge）。
产出 dt_baseline/judge_blackbox.json；replay 模式 diff 分数（容差±5）+理由语义等价人工复核项。
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:28000/api/v2/skills/capability"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "judge_blackbox.json"
TOLERANCE = 5  # 协议 D：数值容差±5

# 1x1 透明 PNG（多模态路径覆盖用）
TINY_PNG = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
            "DwAChwGA60e6kgAAAABJRU5ErkJggg==")

SAMPLES = [
    # ---- 选择题（对/错/空）----
    {"id": "S01_choice_correct", "kind": "correct", "question_type": "single_choice",
     "question": "地球绕太阳公转一周的时间大约是？", "options": ["A. 一天", "B. 一个月", "C. 一年", "D. 十年"],
     "correct_answer": "C", "explanation": "公转周期约一年。", "user_answer": "C"},
    {"id": "S02_choice_wrong", "kind": "wrong", "question_type": "single_choice",
     "question": "水的化学式是？", "options": ["A. H2O", "B. CO2", "C. O2", "D. NaCl"],
     "correct_answer": "A", "explanation": "水由两个氢原子和一个氧原子组成。", "user_answer": "B"},
    {"id": "S03_choice_empty", "kind": "empty", "question_type": "single_choice",
     "question": "光在真空中的传播速度约为？", "options": ["A. 340m/s", "B. 3×10^8 m/s", "C. 150km/h", "D. 7.9km/s"],
     "correct_answer": "B", "explanation": "真空光速约每秒三十万公里。", "user_answer": ""},
    # ---- 判断题（对/错/空）----
    {"id": "S04_judge_correct", "kind": "correct", "question_type": "true_false",
     "question": "0 是偶数。", "correct_answer": "对", "explanation": "0 能被 2 整除。", "user_answer": "对"},
    {"id": "S05_judge_wrong", "kind": "wrong", "question_type": "true_false",
     "question": "所有的质数都是奇数。", "correct_answer": "错", "explanation": "2 是质数且是偶数。", "user_answer": "对"},
    {"id": "S06_judge_empty", "kind": "empty", "question_type": "true_false",
     "question": "植物夜间也进行光合作用。", "correct_answer": "错", "explanation": "光合作用需要光照。", "user_answer": ""},
    # ---- 填空题（对/半对/错/空）----
    {"id": "S07_fill_correct", "kind": "correct", "question_type": "fill",
     "question": "一年有____个月。", "correct_answer": "12", "explanation": "历法常识。", "user_answer": "12"},
    {"id": "S08_fill_half", "kind": "half", "question_type": "fill",
     "question": "中国的首都是____。", "correct_answer": "北京", "explanation": "", "user_answer": "中国的首都北京"},
    {"id": "S09_fill_wrong", "kind": "wrong", "question_type": "fill",
     "question": "圆周率精确到两位小数是____。", "correct_answer": "3.14", "explanation": "π≈3.14159。", "user_answer": "3.41"},
    {"id": "S10_fill_empty", "kind": "empty", "question_type": "fill",
     "question": "世界上面积最大的洋是____。", "correct_answer": "太平洋", "explanation": "", "user_answer": ""},
    # ---- 简答题（对/半对/错/空）----
    {"id": "S11_short_correct", "kind": "correct", "question_type": "short_answer",
     "question": "简述光合作用的原材料。", "correct_answer": "二氧化碳和水",
     "explanation": "光合作用：二氧化碳+水 在光照下生成有机物和氧气。", "user_answer": "原材料是二氧化碳和水"},
    {"id": "S12_short_half", "kind": "half", "question_type": "short_answer",
     "question": "简述光合作用的原材料。", "correct_answer": "二氧化碳和水",
     "explanation": "两个原材料。", "user_answer": "需要二氧化碳"},
    {"id": "S13_short_wrong", "kind": "wrong", "question_type": "short_answer",
     "question": "简述光合作用的原材料。", "correct_answer": "二氧化碳和水",
     "explanation": "", "user_answer": "光合作用的原材料是土壤和肥料"},
    {"id": "S14_short_empty", "kind": "empty", "question_type": "short_answer",
     "question": "简述四季成因。", "correct_answer": "地球公转与地轴倾斜导致太阳直射点周期移动。",
     "explanation": "", "user_answer": ""},
    # ---- 计算题（对/半对/错/空）----
    {"id": "S15_calc_correct", "kind": "correct", "question_type": "calc",
     "question": "计算 25×4+10。", "correct_answer": "110", "explanation": "25×4=100，+10=110。", "user_answer": "110"},
    {"id": "S16_calc_half", "kind": "half", "question_type": "calc",
     "question": "计算 25×4+10。", "correct_answer": "110", "explanation": "过程对结果错给部分分。",
     "user_answer": "25×4=100，所以答案是 100"},
    {"id": "S17_calc_wrong", "kind": "wrong", "question_type": "calc",
     "question": "计算 12+13。", "correct_answer": "25", "explanation": "", "user_answer": "26"},
    {"id": "S18_calc_empty", "kind": "empty", "question_type": "calc",
     "question": "计算 7×8。", "correct_answer": "56", "explanation": "", "user_answer": ""},
    # ---- 多选（对/半对/错）----
    {"id": "S19_multi_correct", "kind": "correct", "question_type": "multi_choice",
     "question": "以下哪些是哺乳动物？", "options": ["A. 鲸", "B. 鲨鱼", "C. 蝙蝠", "D. 鳄鱼"],
     "correct_answer": "A,C", "explanation": "鲸和蝙蝠是哺乳动物。", "user_answer": "A,C"},
    {"id": "S20_multi_half", "kind": "half", "question_type": "multi_choice",
     "question": "以下哪些是哺乳动物？", "options": ["A. 鲸", "B. 鲨鱼", "C. 蝙蝠", "D. 鳄鱼"],
     "correct_answer": "A,C", "explanation": "漏选给部分分。", "user_answer": "A"},
    {"id": "S21_multi_wrong", "kind": "wrong", "question_type": "multi_choice",
     "question": "以下哪些是哺乳动物？", "options": ["A. 鲸", "B. 鲨鱼", "C. 蝙蝠", "D. 鳄鱼"],
     "correct_answer": "A,C", "explanation": "", "user_answer": "B,D"},
    # ---- 图片题（多模态路径覆盖 ×2）----
    {"id": "S22_image_answered", "kind": "half", "question_type": "short_answer",
     "question": "看图写出你看到的几何形状名称。", "correct_answer": "三角形",
     "explanation": "图中为一个三角形。", "user_answer": "好像是一个三角形",
     "user_answer_images": [{"filename": "answer.png", "mime_type": "image/png", "base64": TINY_PNG}]},
    {"id": "S23_image_empty", "kind": "empty", "question_type": "short_answer",
     "question": "看图写出你看到的几何形状名称。", "correct_answer": "三角形",
     "explanation": "", "user_answer": "",
     "user_answer_images": [{"filename": "answer.png", "mime_type": "image/png", "base64": TINY_PNG}]},
    # ---- 边界：题面为空 ----
    {"id": "S24_edge_noquestion", "kind": "empty", "question_type": "short_answer",
     "question": "", "correct_answer": "任意", "explanation": "", "user_answer": "不知道"},
]


mode_global = {"phase": "pre"}


def judge_one(sample: dict) -> dict:
    """经桥跑一条判分样本，返回 {sample, result_text, done_ok, elapsed_s}。"""
    skill = "sishu/quiz" if mode_global["phase"] == "post" else "tutor/quiz"
    body = {
        "skill_code": skill,
        "action": "judge",
        "session_id": None,
        "message": sample.get("question") or "(题面为空)",
        "config": {
            "action": "judge",
            "language": "zh",
            "question": sample.get("question", ""),
            "question_type": sample.get("question_type", ""),
            "options": sample.get("options"),
            "correct_answer": sample.get("correct_answer", ""),
            "explanation": sample.get("explanation", ""),
            "user_answer": sample.get("user_answer", ""),
            "user_answer_images": sample.get("user_answer_images"),
        },
        "tools": [], "knowledge_bases": [], "attachments": [], "history_references": [],
    }
    req = urllib.request.Request(BASE, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    result_text, done_ok, error_text = "", None, None
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except Exception:
                continue
            if ev.get("type") == "result":
                result_text = ev.get("content", "")
            elif ev.get("type") == "error":
                error_text = ev.get("content", "")
            elif ev.get("type") == "done":
                done_ok = bool((ev.get("metadata") or {}).get("ok"))
    return {"id": sample["id"], "kind": sample["kind"], "question_type": sample["question_type"],
            "request": {k: sample.get(k) for k in ("question", "question_type", "options",
                                                    "correct_answer", "explanation", "user_answer")},
            "has_image": bool(sample.get("user_answer_images")),
            "result_text": result_text, "error": error_text,
            "done_ok": done_ok, "elapsed_s": round(time.time() - t0, 1)}


def record(out_path: Path, phase: str) -> None:
    mode_global["phase"] = phase
    outs = []
    for i, s in enumerate(SAMPLES, 1):
        r = judge_one(s)
        outs.append(r)
        print(f"[{i}/{len(SAMPLES)}] {r['id']} ok={r['done_ok']} {r['elapsed_s']}s "
              f"result[:60]={r['result_text'][:60]!r}")
    out_path.write_text(json.dumps({"date": time.strftime("%Y-%m-%d %H:%M"),
                                    "bridge_skill": "sishu/quiz" if phase == "post" else "tutor/quiz",
                                    "action": "judge", "phase": phase,
                                    "tolerance": TOLERANCE, "samples": outs},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {len(outs)} samples -> {out_path}")


def replay() -> None:
    """批3 重放：批0 基线（pre）vs 批3 重写态（post，skill=sishu/quiz）逐例并排 diff。"""
    base = json.loads(OUT.read_text(encoding="utf-8"))
    mode_global["phase"] = "post"
    diffs, misses = [], []
    for orig in base["samples"]:
        sample = {"id": orig["id"], "kind": orig["kind"], "question_type": orig["question_type"],
                  **orig["request"],
                  "user_answer_images": [{"base64": TINY_PNG}] if orig.get("has_image") else None}
        r = judge_one(sample)
        if r["error"] or not r["done_ok"]:
            misses.append({"id": orig["id"], "error": r["error"]})
            continue
        diffs.append({"id": orig["id"], "before": orig["result_text"], "after": r["result_text"],
                      "within_tolerance": "MANUAL_REVIEW（分数±5+理由语义等价）"})
    out = {"tolerance": TOLERANCE, "diffs": diffs, "failures": misses}
    rp = OUT.parent / "judge_blackbox_replay.json"
    rp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"replay: {len(diffs)} diffs, {len(misses)} failures -> {rp}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "record"
    if mode == "record":
        record(OUT, "pre")
    elif mode == "record-post":
        record(OUT.parent / "judge_blackbox_v4b3.json", "post")
    elif mode == "replay":
        replay()
    else:
        print("usage: _v4_judge_blackbox.py [record|replay]")
        sys.exit(2)
