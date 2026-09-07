# -*- coding: utf-8 -*-
"""_seed_16a.py - 批16-A 金标种子：场景 COUNT 题已验证问答对入库（幂等）。

SQL 单源（实施偏离登记）：plan 原设计取 MetricQueryLog 最近成功执行的 executed_sql，
实施实测该表全空（0 行）——Agent 链路 execute_doris_sql 走 MCP 不落 MetricQueryLog
（该表属 metric_center 链）。改用**模板文件解析链**为单源：
distribution-overload/templates/step2_count_overload.sql（14-A e2e 验证出表
重过载台区数/过载台区数/重载台区数/判定台区总数 = 2/1/1/2 的同一 SQL），经
resolve_entity_aliases + _resolve_entity_refs 解析为物理表名可执行 SQL——
与 14-A e2e 实际执行并出表的 SQL 同源同链。
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.base import KgGoldenQaSet
from app.services.golden_qa_service import add_golden, search_golden_qa
from app.services.template_guard import _resolve_entity_refs, load_template, resolve_entity_aliases
from app.services.skill_catalog import get_catalog

QUESTION = "统计重过载台区数量"


def _strip_sql_comments(sql: str) -> str:
    """剥 -- 行注释与 /* */ 块注释（保留字符串字面量内的内容）。

    实测依据（scripts/_diag_16a_comment.py）：doris_engine 执行链对含 `--` 注释的
    SQL 全崩（连 `SELECT 1 -- simple note` 都语法错）——注释对执行语义无贡献，剥除。
    """
    import re
    out = []
    for line in sql.splitlines():
        res = []
        in_str = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                res.append(ch)
                if ch == "'" and i > 0 and line[i - 1] != "\\":
                    in_str = False
                i += 1
                continue
            if ch == "'":
                in_str = True
                res.append(ch)
                i += 1
                continue
            if ch == "-" and line[i:i + 2] == "--":
                break  # 行注释：丢弃行内余下内容
            res.append(ch)
            i += 1
        out.append("".join(res))
    no_block = re.sub(r"/\*.*?\*/", "", "\n".join(out), flags=re.DOTALL)
    return "\n".join(l for l in no_block.splitlines() if l.strip()).strip()


def _verified_sql() -> str:
    skill = get_catalog().load_skill("distribution-overload")
    raw = load_template(skill.path.parent / "templates/step2_count_overload.sql")
    resolved = _resolve_entity_refs(resolve_entity_aliases(raw, skill.entity_aliases))
    return _strip_sql_comments(resolved)


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(KgGoldenQaSet).filter(KgGoldenQaSet.question == QUESTION).first():
            print(f"[skip] 金标已存在: {QUESTION}")
        else:
            sql = _verified_sql()
            if not sql or "COUNT" not in sql:
                sys.exit("[fail] 模板解析失败或非 COUNT 形态")
            # digest 用 Doris 同链自算（_exec_for_digest 按三段名路由会把无前缀物理表
            # SQL 路由到 PG 而失败；本表实际在 Doris internal 联邦目录——与 Agent 14-A
            # 实际执行一致）；engine 显式 doris（_infer_engine 同样按三段名，无前缀误判 physical）
            from app.services.doris_engine import execute_sql
            from app.services.golden_qa_service import compute_result_digest
            res = execute_sql(sql)
            if res.get("error") or not res.get("rows"):
                sys.exit(f"[fail] 期望 SQL Doris 执行失败: {str(res.get('error'))[:200]}")
            digest = compute_result_digest(res["rows"], res.get("row_count") or len(res["rows"]))
            out = add_golden(db, question=QUESTION, expected_sql=sql,
                             expected_result_digest=digest,
                             route_type="scenario", scenario_tag="distribution-overload",
                             engine="doris")
            print(f"[seed] ok={out.get('ok')} id={out.get('id')} rows={res['rows']}")
        hits = search_golden_qa(db, QUESTION)
        print(f"[verify] top={[(h.get('score'), h.get('question')) for h in hits[:2]]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
