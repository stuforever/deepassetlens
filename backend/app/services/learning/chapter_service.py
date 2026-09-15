# -*- coding: utf-8 -*-
"""⑤补补-3 步骤 1：chapter 聚合服务（D2 语义一屏：章节信息/知识点明细+精讲/错题/掌握度）。

图谱面走 graph_query_neo4j._get_driver（种子种子=seed_tutor_curriculum 的节点契约：
ch:{code}=Category{kind:'chapter'}、kp:{code}=Category:Entity{kind:'knowledge_point',
explanation/examples 属性}、kp -BELONGS_TO_CHAIN-> ch）；PG 面走 learning_dao。
"""
from __future__ import annotations

from datetime import datetime, timezone
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


def path_overview(user_id: str) -> dict:
    """⑤补补-4：精通之路数据面——图谱结构（教材→章节=模块→kp）×PG 掌握度→三色映射。

    色（A4 色阶映射，计划补-4 步 2）：无卡=灰未学 / 卡存在且 retention<0.7=蓝学习中 /
    retention≥pass_threshold(0.7)=绿已精通。
    """
    driver = _get_driver()
    with driver.session() as s:
        textbooks = s.run(
            "MATCH (t:Category {kind:'textbook'}) RETURN t.code AS code, t.name AS name ORDER BY t.code"
        ).data()
        rows = s.run(
            "MATCH (k:Category:Entity {kind:'knowledge_point'})-[:BELONGS_TO_CHAIN]->(c:Category {kind:'chapter'}) "
            "OPTIONAL MATCH (c)-[:BELONGS_TO_CHAIN]->(t:Category {kind:'textbook'}) "
            "RETURN k.code AS kp_code, k.name AS kp_name, c.code AS ch_code, c.name AS ch_name, "
            "t.code AS tb_code, t.name AS tb_name ORDER BY c.code, k.code").data()

    kp_codes = [r["kp_code"] for r in rows]
    cards: dict[str, dict] = {}
    if kp_codes:
        with _engine.begin() as c:
            for r in c.execute(text(
                "SELECT item_id, stability, reps, lapses, last_review FROM learning_review_cards "
                "WHERE user_id=:u AND kind='knowledge_point' AND item_id = ANY(:kps)"),
                {"u": user_id, "kps": kp_codes}).mappings().all():
                cards[r["item_id"]] = dict(r)

    def _ret(stability: float, last_review) -> float:
        if not last_review or not stability or stability <= 0:
            return 0.0
        t = max(0.0, (datetime.now(timezone.utc) - last_review).total_seconds() / 86400.0)
        return float((1.0 + t / (3.0 * stability)) ** -0.5)

    PASS_THRESHOLD = 0.7                       # DeepTutor LearningModule.pass_threshold 语义
    modules: dict[str, dict] = {}
    for r in rows:
        m = modules.setdefault(r["ch_code"], {
            "code": r["ch_code"], "name": r["ch_name"],
            "textbook": r.get("tb_name") or "", "kps": [],
        })
        card = cards.get(r["kp_code"])
        if card is None:
            color, retention = "gray", 0.0
        else:
            retention = round(_ret(float(card.get("stability") or 0), card.get("last_review")), 4)
            color = "green" if retention >= PASS_THRESHOLD else "blue"
        m["kps"].append({
            "code": r["kp_code"], "name": r["kp_name"], "color": color, "retention": retention,
            "stability": float(card["stability"]) if card else 0.0,
        })

    # 模块级聚合色：全绿=绿（已精通）/部分有卡=蓝（学习中）/全无卡=灰（未学）
    module_list = []
    for m in modules.values():
        colors = [k["color"] for k in m["kps"]]
        m["color"] = "green" if colors and all(c == "green" for c in colors) else (
            "blue" if any(c != "gray" for c in colors) else "gray")
        module_list.append(m)
    module_list.sort(key=lambda x: x["code"])

    return {
        "textbooks": [{"code": t["code"], "name": t["name"]} for t in textbooks],
        "modules": module_list,                       # LearningModule 语义：章节=kp 组合
        "pass_threshold": PASS_THRESHOLD,
    }


__all__ = ["chapters_list", "chapter_overview", "path_overview"]
