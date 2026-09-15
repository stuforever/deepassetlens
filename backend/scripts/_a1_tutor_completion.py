# -*- coding: utf-8 -*-
"""⑤补补-1 步骤 4：A1 验收断言（图谱章节树/精讲可读/母题挂图谱）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j import GraphDatabase
from sqlalchemy import text

from scripts import seed_tutor_curriculum as seed
from app.services.learning.pg import _engine

ok = []
d = GraphDatabase.driver(seed._NEO4J_URI, auth=(seed._NEO4J_USER, seed._NEO4J_PWD))
with d.session() as s:
    r1 = s.run(
        "MATCH (k:Entity {code:'kp:正数与负数'})-[:BELONGS_TO_CHAIN]->(c)-[:BELONGS_TO_CHAIN]->(t) "
        "RETURN k.name AS kn, c.name AS cn, t.name AS tn").single()
    ok.append(("图谱章节树（kp→章节→教材链）",
               r1 is not None and r1["tn"] == "初中数学七上",
               str(dict(r1)) if r1 else "无"))
    r2 = s.run(
        "MATCH (k:Entity {code:'kp:正数与负数'}) "
        "RETURN k.explanation AS e, size(k.examples) AS n").single()
    ok.append(("知识点精讲可读（节点属性）",
               r2 is not None and len(r2["e"] or "") > 30 and r2["n"] >= 2,
               f"expl {len(r2['e'] or '')} 字/examples {r2['n']}" if r2 else "无"))
d.close()

with _engine.begin() as c:
    rows = c.execute(text("SELECT mq_id, knowledge_point_id FROM learning_mother_questions")).mappings().all()
d = GraphDatabase.driver(seed._NEO4J_URI, auth=(seed._NEO4J_USER, seed._NEO4J_PWD))
with d.session() as s:
    matched = sum(1 for r in rows
                  if s.run("MATCH (n {code:$c}) RETURN 1 AS x", {"c": r["knowledge_point_id"]}).single() is not None)
d.close()
ok.append(("母题 ≥3 且全部挂真实 kp 节点", len(rows) >= 3 and matched == len(rows), f"{len(rows)} 条/挂上 {matched}"))

for name, good, detail in ok:
    print(("PASS" if good else "FAIL"), name, detail)
sys.exit(0 if all(g for _, g, _ in ok) else 1)
