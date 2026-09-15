# -*- coding: utf-8 -*-
"""⑤补补-1 步骤 3：课程骨架种子——教材/章节/知识点=图谱节点+边（MERGE 幂等）+母题 ≥3。

- 沿 graph_query_neo4j.py L305/L358 模式：MERGE Category{code} 节点+HAS_PARENT/BELONGS_TO_CHAIN 边；
- 精讲/实例=知识点节点属性（D1 判定——SET k.explanation/k.examples）；
- 母题种子=PG learning_mother_questions（ON CONFLICT (mq_id) DO NOTHING 幂等，D7 挂真实 kp 节点）；
- 种子是管理动作可重放（spec Runbook 步 3：种子可删可重种）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from neo4j import GraphDatabase          # noqa: E402
from sqlalchemy import text              # noqa: E402

from app.services.learning.pg import _engine   # noqa: E402

_NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PWD = os.environ.get("NEO4J_PASSWORD", "")

# ⑤补 D1 种子数据（教材/章节/知识点——1.1 章两知识点起步，后续批扩）
SEED = {
    "code": "textbook:初中数学七上",
    "name": "初中数学七上",
    "chapters": [
        {"code": "ch:7a-1-1", "name": "1.1_正数和负数", "kps": [
            {"code": "kp:正数与负数", "name": "正数与负数",
             "explanation": "大于 0 的数叫正数，正数前可加「+」；在正数前面加上「-」号的数叫负数；"
                            "0 既不是正数也不是负数。正负数表示具有相反意义的量（收入/支出、向东/向西）。",
             "examples": ["+5 是正数；-3 是负数；0 既非正也非负。",
                          "收入 100 元记作 +100，支出 80 元记作 -80。"]},
            {"code": "kp:有理数", "name": "有理数",
             "explanation": "整数与分数统称有理数。整数含正整数、零、负整数；分数含正分数与负分数。"
                            "有理数都可以写成两个整数之比（p/q，q≠0）。",
             "examples": ["-2, 0, 3, 1/4, -0.5 都是有理数。"]},
        ]},
    ],
}

MOTHER_QUESTIONS = [
    {"mq_id": "mq-seed-0001", "title": "负数判断母题",
     "archetype_text": "判断下列各数哪些是负数：-3, 0, +2.5, -1/2, 7。",
     "knowledge_point_id": "kp:正数与负数"},
    {"mq_id": "mq-seed-0002", "title": "相反意义量母题",
     "archetype_text": "收入 100 元记作 +100，那么支出 80 元记作什么？两者相差多少？",
     "knowledge_point_id": "kp:正数与负数"},
    {"mq_id": "mq-seed-0003", "title": "有理数分类母题",
     "archetype_text": "把 -2, 0, 3, 1/4, -0.5 按整数/分数分类，并说明哪些是有理数。",
     "knowledge_point_id": "kp:有理数"},
]


def _merge_tx(tx, seed: dict) -> None:
    """逐层 MERGE（幂等）：教材→章节→知识点（属性=精讲/实例）。"""
    tx.run(
        "MERGE (t:Category {code:$code}) "
        "SET t.name=$name, t.kind='textbook'",
        {"code": seed["code"], "name": seed["name"]},
    )
    for ch in seed["chapters"]:
        tx.run(
            "MERGE (t:Category {code:$tcode}) "
            "MERGE (c:Category {code:$code}) "
            "SET c.name=$name, c.kind='chapter' "
            "MERGE (c)-[:BELONGS_TO_CHAIN]->(t) "
            "MERGE (c)-[:HAS_PARENT]->(t)",
            {"tcode": seed["code"], "code": ch["code"], "name": ch["name"]},
        )
        for kp in ch["kps"]:
            tx.run(
                "MERGE (c:Category {code:$ccode}) "
                "MERGE (k:Category:Entity {code:$code}) "
                "SET k.name=$name, k.kind='knowledge_point', k.explanation=$expl, k.examples=$exs "
                "MERGE (k)-[:BELONGS_TO_CHAIN]->(c) "
                "MERGE (k)-[:HAS_PARENT]->(c)",
                {"ccode": ch["code"], "code": kp["code"], "name": kp["name"],
                 "expl": kp["explanation"], "exs": kp["examples"]},
            )


def seed_graph() -> None:
    driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PWD))
    try:
        with driver.session() as session:
            session.execute_write(_merge_tx, SEED)
    finally:
        driver.close()


def seed_mother_questions() -> int:
    """母题 ≥3（ON CONFLICT 幂等）。返回本次新插行数。"""
    inserted = 0
    with _engine.begin() as c:
        for m in MOTHER_QUESTIONS:
            r = c.execute(text(
                "INSERT INTO learning_mother_questions "
                "(mq_id, title, archetype_text, knowledge_point_id) "
                "VALUES (:mid, :title, :arch, :kp) "
                "ON CONFLICT (mq_id) DO NOTHING"),
                {"mid": m["mq_id"], "title": m["title"], "arch": m["archetype_text"],
                 "kp": m["knowledge_point_id"]})
            inserted += r.rowcount or 0
    return inserted


def count_nodes() -> int:
    """种子范围节点数（textbook/chapter/knowledge_point 三 kind）。"""
    driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PWD))
    try:
        with driver.session() as session:
            rec = session.run(
                "MATCH (n) WHERE n.kind IN ['textbook','chapter','knowledge_point'] "
                "RETURN count(n) AS c").single()
            return int(rec["c"])
    finally:
        driver.close()


def count_mother_questions() -> int:
    with _engine.begin() as c:
        rec = c.execute(text("SELECT count(*) AS c FROM learning_mother_questions")).mappings().first()
    return int(rec["c"])


def main() -> None:
    seed_graph()
    seed_mother_questions()
    print(f"种子完成：图谱节点 {count_nodes()}（textbook/chapter/kp）母题 {count_mother_questions()} 条")


if __name__ == "__main__":
    main()
