# -*- coding: utf-8 -*-
"""⑤补补-3 步骤 1：chapter 聚合服务（D2 语义一屏：章节信息/知识点明细+精讲/错题/掌握度）。

图谱面走 graph_query_neo4j._get_driver（种子种子=seed_tutor_curriculum 的节点契约：
ch:{code}=Category{kind:'chapter'}、kp:{code}=Category:Entity{kind:'knowledge_point',
explanation/examples 属性}、kp -BELONGS_TO_CHAIN-> ch）；PG 面走 learning_dao。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import text

from app.services.graph_query_neo4j import _get_driver
from .pg import _engine


def chapters_list() -> list[dict]:
    """图谱全部章节（chapter 节点+所属教材名）。"""
    driver = _get_driver()
    with driver.session() as s:
        recs = s.run(
            "MATCH (c:Category {kind:'chapter'}) OPTIONAL MATCH (t:Category {kind:'textbook'})<-[:BELONGS_TO_CHAIN]-(c) "
            "RETURN c.code AS code, c.name AS name, t.name AS textbook ORDER BY code").data()
    return [{"code": r["code"], "name": r["name"], "textbook": r.get("textbook") or ""} for r in recs]


def chapter_overview(chapter_id: str, user_id: str) -> Optional[dict]:
    """一屏聚合：章节信息/知识点明细（精讲+掌握度）/该章节错题/今日任务数。"""
    driver = _get_driver()
    with driver.session() as s:
        ch = s.run(
            "MATCH (c:Category {kind:'chapter', code:$code}) "
            "RETURN c.code AS code, c.name AS name", {"code": chapter_id}).single()
        if ch is None:
            return None
        kps = s.run(
            "MATCH (k:Category:Entity {kind:'knowledge_point'})-[:BELONGS_TO_CHAIN]->(c:Category {code:$code}) "
            "RETURN k.code AS code, k.name AS name, k.explanation AS explanation, k.examples AS examples "
            "ORDER BY k.code", {"code": chapter_id}).data()

    kp_codes = [k["code"] for k in kps]
    mastery: dict[str, dict] = {}
    wrong: list[dict] = []
    if kp_codes:
        with _engine.begin() as c:
            rows = c.execute(text(
                "SELECT item_id, stability, reps, lapses, due FROM learning_review_cards "
                "WHERE user_id=:u AND kind='knowledge_point' AND item_id = ANY(:kps)"),
                {"u": user_id, "kps": kp_codes}).mappings().all()
            for r in rows:
                mastery[r["item_id"]] = {
                    "reps": r["reps"], "lapses": r["lapses"],
                    "mastery": round(max(0.0, min(1.0, (r["reps"] - r["lapses"]) / r["reps"])), 2) if r["reps"] else 0.0,
                    "stability": r["stability"],
                }
            wrong = [dict(r) for r in c.execute(text(
                "SELECT wq.wq_id, wq.variant_text, wq.status, wq.wrong_at, wq.mother_question_id "
                "FROM learning_wrong_questions wq "
                "JOIN learning_mother_questions mq ON mq.mq_id = wq.mother_question_id "
                "WHERE wq.user_id=:u AND mq.knowledge_point_id = ANY(:kps) "
                "ORDER BY wq.wrong_at DESC LIMIT 20"),
                {"u": user_id, "kps": kp_codes}).mappings().all()]

    return {
        "chapter": {"code": ch["code"], "name": ch["name"]},
        "kps": [{
            "code": k["code"], "name": k["name"],
            "explanation": k.get("explanation") or "",
            "examples": k.get("examples") or [],
            "mastery": mastery.get(k["code"], {}).get("mastery", 0.0),
            "reps": mastery.get(k["code"], {}).get("reps", 0),
        } for k in kps],
        "wrong_questions": [{
            "wq_id": w["wq_id"], "variant_text": w["variant_text"], "status": w["status"],
            "mother_question_id": w["mother_question_id"],
        } for w in wrong],
        "wrong_count": len(wrong),
        "learned_count": sum(1 for k in kps if k["code"] in mastery),
    }


__all__ = ["chapters_list", "chapter_overview"]
