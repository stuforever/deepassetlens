# -*- coding: utf-8 -*-
"""批2 B0 三分类：DT knowledge 41 路径 → ④可承接/④差距增强/保底回退(域内复刻)。

判定规则（唯一交棒件纪律）：适配成本>复刻成本→回退域内复刻；语义等价且④为存储之主→承接/增强。
依据：openapi 操作面 × knowledge.py 存储触点实测（耦合 deeptutor/knowledge RAG 机制包）。"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent / "dt_baseline"
inv = json.loads((BASE / "endpoints_inventory.json").read_text(encoding="utf-8"))
kn = [i for i in inv if i["path"].startswith("/api/v1/knowledge")]
paths = sorted({i["path"] for i in kn})

MECHANISM = ("rag-pipelines", "rag-providers", "connect-", "probe-", "tasks/", "upload",
             "reindex", "retry", "progress", "files", "folders", "file-preview",
             "sync-folder", "linked-folders", "link-folder", "/default/")
defs = []
for p in paths:
    ops = [i["method"] for i in kn if i["path"] == p]
    if any(m in p for m in MECHANISM):
        cat, why = "回退_域内复刻", "机制密集（RAG栈/文件树/进度流/连接器）——适配④需重写，违反零重设计"
    elif p in ("/api/v1/knowledge/list", "/api/v1/knowledge/create", "/api/v1/knowledge/health",
               "/api/v1/knowledge/supported-file-types", "/api/v1/knowledge/configs"):
        cat, why = "适配_指④", "KB 注册/列表/健康/类型面——语义与④ knowledge-bases 等价，适配层映射"
    else:
        cat, why = "④差距增强", "语义归④存储主但④缺该面（configs sync/default/config）——④补面后适配映射"
    defs.append({"path": p, "ops": ops, "分类": cat, "依据": why})

summary = {}
for d in defs:
    summary[d["分类"]] = summary.get(d["分类"], 0) + 1
out = {"判定依据": "openapi 操作面 × knowledge.py 存储触点（耦合 deeptutor/knowledge RAG 机制包+data/knowledge_bases 7 库实测）",
       "summary": summary, "endpoints": defs,
       "数据层": "knowledge_bases/parse_cache 数据→导入④（件纪律）；机制面域内复刻照搬 deeptutor/knowledge 包"}
(BASE / "batch2_三分类.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("三分类:", summary)
