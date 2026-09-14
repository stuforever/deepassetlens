# -*- coding: utf-8 -*-
"""⑤b（spec §五诚实账①）：select_exercises 图谱邻居扩展——本批唯一新算法语义。
邻居池=本知识点+前置/后继（批 0.3 实测关系：RELATES_TO/HAS_PARENT/BELONGS_TO_CHAIN）；
母题按掌握度加权（掌握度低→权高）→top-n。真实图谱联调放⑤f（本批 mock 测试）。"""
from __future__ import annotations

from typing import Any


def _graph_neighbors(knowledge_point_id: str, depth: int = 1) -> list[str]:
    """Neo4j 邻居查询（批 0.3 实测锚点：node.entity_id 主键）。
    图不可用→返回仅本节点（退化单点池——不静默吞错，记日志）。"""
    if not knowledge_point_id:
        return []
    import os
    try:
        from neo4j import GraphDatabase
        uri = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        pwd = os.environ.get("NEO4J_PASSWORD", "")
        if not pwd:
            from pathlib import Path
            for f in (Path(__file__).resolve().parents[4] / ".env.infra",
                      Path(__file__).resolve().parents[4] / ".env"):
                if f.exists():
                    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                        if line.strip().startswith("NEO4J_PASSWORD"):
                            pwd = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                    if pwd:
                        break
        drv = GraphDatabase.driver(uri, auth=(user, pwd))
        with drv.session() as s:
            recs = s.run(
                "MATCH (n {entity_id: $id})-[r]-(m) WHERE type(r) IN ['RELATES_TO','HAS_PARENT'] "
                "RETURN coalesce(m.entity_id, m.code, '') AS nid LIMIT 20",
                {"id": knowledge_point_id})
            nids = [r["nid"] for r in recs if r["nid"]]
        drv.close()
        return [knowledge_point_id] + [x for x in nids if x != knowledge_point_id]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("图谱邻居扩展退化（单点池）: %s", e)
        return [knowledge_point_id]


def _mastery_weight(user_id: str, knowledge_point_id: str) -> float:
    """掌握度→权重（掌握度低→权高）：w = 1.05 - mastery ∈ [0.05, 1.05]。"""
    from app.services.learning.service import mastery_query
    try:
        m = mastery_query(user_id, knowledge_point_id).get("mastery", 0.0)
    except Exception:
        m = 0.0
    return round(1.05 - float(m or 0.0), 4)


def _weighted_pick(mqs: list[dict], weights: dict[str, float], n: int) -> dict:
    """加权 top-n（稳定排序：权重降序→mq_id 升序；随机性不进选题——可复现）。"""
    scored = sorted(mqs, key=lambda mq: (-weights.get(mq["mq_id"], 1.0), mq["mq_id"]))
    picked = scored[:max(1, min(int(n), 50))]
    return {"count": len(picked),
            "items": [{**mq, "weight": weights.get(mq["mq_id"], 1.0)} for mq in picked]}


def select_exercises_with_neighbors(user_id: str, knowledge_point_id: str,
                                    n: int = 5, band: str | None = None) -> dict:
    """工具引擎：邻居池→母题→掌握度加权→top-n。"""
    from app.services.learning import learning_dao as _dao
    kps = _graph_neighbors(knowledge_point_id)
    mqs = _dao.mother_questions_by_kps(kps)
    weights = {mq["mq_id"]: _mastery_weight(user_id, mq["knowledge_point_id"]) for mq in mqs}
    out = _weighted_pick(mqs, weights, n)
    out["knowledge_point_id"] = knowledge_point_id
    out["neighbor_pool"] = kps
    if band:
        out["band"] = band
    return out
