# -*- coding: utf-8 -*-
"""⑤R B0 2.4：L2 适配端点对拍——原仓 kb_config.json 真实 KB 注册表 → 导入④（数据分区执行）。

对拍口径：导入返回计数 × ④行形状（name/description/status/pointer_params.source/kb_name）
逐项核对原仓 kb_config.json；幂等重跑零重复。导入行保留（生产数据迁移语义）。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DT_CFG = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\data\knowledge_bases\kb_config.json")
cfg = json.loads(DT_CFG.read_text(encoding="utf-8"))
kbs = cfg.get("knowledge_bases", {})
print("原仓 KB 注册表:", len(kbs), "库:", sorted(kbs.keys()))

from app.api import knowledge_base as kb_api  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.knowledge_base import KnowledgeBase  # noqa: E402

WS = str(DT_CFG.parent)
items = []
for name, info in kbs.items():
    items.append(kb_api.KBImport.Item(
        name=name,
        description=info.get("description"),
        status=info.get("status") or "ready",
        pointer_params={"source": "tutor", "workspace": WS, "kb_name": name},
    ))
payload = kb_api.KBImport(source="tutor", items=items)

db = SessionLocal()
try:
    out1 = kb_api.import_knowledge_bases(payload, db)
    print("首跑:", {k: v for k, v in out1["data"].items() if k != "names"})
    out2 = kb_api.import_knowledge_bases(payload, db)
    print("重跑(幂等):", {k: v for k, v in out2["data"].items() if k != "names"})
    assert out2["data"]["imported"] == 0, "幂等破坏——重跑出现新导入"

    rows = db.query(KnowledgeBase).filter(
        KnowledgeBase.type == "connected",
        KnowledgeBase.rag_provider == "tutor_dt").all()
    by_name = {r.name: r for r in rows}
    assert len(rows) == len(kbs), f"行数 {len(rows)} != 注册表 {len(kbs)}"
    mismatch = []
    for name, info in kbs.items():
        r = by_name.get(name)
        if not r:
            mismatch.append(f"{name}: 行缺失")
            continue
        if (r.description or None) != (info.get("description") or None):
            mismatch.append(f"{name}: description 漂移")
        if (r.status or "ready") != (info.get("status") or "ready"):
            mismatch.append(f"{name}: status {r.status} != {info.get('status')}")
        pp = r.pointer_params or {}
        if pp.get("source") != "tutor" or pp.get("kb_name") != name:
            mismatch.append(f"{name}: pointer_params 漂移 {pp}")
    print("对拍不一致:", mismatch if mismatch else "零——L2 通过")
    assert not mismatch
    print("L2 适配对拍 PASS：", len(rows), "行 tutor 域注册表已入④（保留=数据迁移语义）")
finally:
    db.close()
