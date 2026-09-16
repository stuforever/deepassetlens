# -*- coding: utf-8 -*-
"""⑤R E1 7.2：L1 映射审计——域工具面↔复刻端点能力映射清单（每工具映射一端点、零缺失）。

左源=1.5 能力清单冻结（batch1_对账.json 能力×35 tags）+ TUTOR_TOOLS 11 件 +
vendor 挂载面（tutor_routers 17 对路由的机械路由枚举）。输出：dt_baseline/batch7_映射审计.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "vendor"))

import os  # noqa: E402
os.environ.setdefault("DEEPTUTOR_HOME",
                      str(Path(__file__).resolve().parents[1] / "data" / "experts" / "tutor" / "workspace"))

from deeptutor.api.routers import (  # noqa: E402
    book, dashboard, h5_links, imports, knowledge,  # noqa: F401
    learner_profile, mastery_path, mother_question, notebook,  # noqa: F401
    question, question_notebook, quiz_judge, self_learning,  # noqa: F401
)
from deeptutor.learning.curriculum import router as curriculum_router  # noqa: E402

ROUTERS = {
    "mother-questions": (mother_question.router, "/api/v1/mother-questions"),
    "curriculum": (curriculum_router, "/api/v1/curriculum"),
    "knowledge": (knowledge.router, "/api/v1/knowledge"),
    "learning(learner-profile)": (learner_profile.router, "/api/v1/learning"),
    "learning(mastery-path)": (mastery_path.router, "/api/v1/learning"),
    "self-learning": (self_learning.router, "/api/v1/self-learning"),
    "question(WS)": (question.router, "/api/v1/question"),
    "quiz-judge(WS)": (quiz_judge.router, "/api/v1"),
    "notebook": (notebook.router, "/api/v1/notebook"),
    "question-notebook": (question_notebook.router, "/api/v1/question-notebook"),
    "book": (book.router, "/api/v1/book"),
    "imports": (imports.router, "/api/v1/imports"),
    "dashboard": (dashboard.router, "/api/v1/dashboard"),
    "h5-links": (h5_links.router, "/api/v1/h5-links"),
}

# 工具→端点映射（端点=复刻 vendor 面；impl=进程内单源 twin，能力同源）
MAPPING = {
    "fsrs_due": {"endpoints": ["GET /api/v1/mother-questions/reviews/due", "GET /api/v1/mother-questions/reviews/due_count"], "capability": "到期复习清单"},
    "fsrs_review": {"endpoints": ["POST /api/v1/mother-questions/{mid}/review/submit"], "capability": "FSRS 复习评分调度"},
    "mastery_query": {"endpoints": ["GET /api/v1/learning/learner-profile"], "capability": "知识点掌握度"},
    "grade_answer": {"endpoints": ["WS /api/v1/question/judge"], "capability": "判分（原仓判分 WS）"},
    "generate_practice": {"endpoints": ["WS /api/v1/question/generate", "POST /api/v1/learning/generate-practice"], "capability": "变式练习生成"},
    "select_exercises": {"endpoints": ["GET /api/v1/learning/practice", "GET /api/v1/learning/practice/rotate"], "capability": "选题+邻居扩展"},
    "wrong_question_add": {"endpoints": ["POST /api/v1/mother-questions"], "capability": "错题入库（母题面）"},
    "wrong_question_query": {"endpoints": ["GET /api/v1/mother-questions", "GET /api/v1/question-notebook/entries"], "capability": "错题列表"},
    "export_wrong_book": {"endpoints": ["POST /api/v1/mother-questions/export"], "capability": "错题本导出（tab_export 纪律）"},
    "mother_question_find_or_create": {"endpoints": ["GET /api/v1/mother-questions", "POST /api/v1/mother-questions"], "capability": "母题搜建（组合面：GET 搜+POST 建）"},
    "analyze_wrong_questions": {"endpoints": ["GET /api/v1/mother-questions/analysis/error-patterns"], "capability": "错因聚合分析"},
}

# 机械枚举 vendored 路由全路径（HTTP+WS）
live: set[str] = set()
for _tag, (router, prefix) in ROUTERS.items():
    for r in router.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None)
        if methods:
            for m in methods:
                live.add(f"{m} {prefix}{path}")
        else:
            live.add(f"WS {prefix}{path}")

results = {}
missing = []
for tool, m in MAPPING.items():
    hits = []
    for ep in m["endpoints"]:
        if ep in live:
            hits.append(ep)
    results[tool] = {"capability": m["capability"], "endpoints": m["endpoints"],
                     "verified": hits, "ok": len(hits) == len(m["endpoints"])}
    if not results[tool]["ok"]:
        missing.append((tool, [e for e in m["endpoints"] if e not in live]))

out = {"tools_total": len(MAPPING), "ok": sum(1 for v in results.values() if v["ok"]),
       "vendor_routes_total": len(live), "results": results}
p = Path(__file__).resolve().parent / "dt_baseline" / "batch7_映射审计.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"映射审计: {out['ok']}/{out['tools_total']} 工具全端点命中（vendor 路由 {out['vendor_routes_total']} 条）")
for t, miss in missing:
    print("  缺:", t, miss)
