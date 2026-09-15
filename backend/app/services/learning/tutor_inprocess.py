# -*- coding: utf-8 -*-
"""教学九工具单源 impl + 进程内 twin（🔴-4，审查 2026-09-15）。

背景：九件原走 HTTP SSE 跳数（独立 ASGI 请求全新 context）→ ContextVar 恒 None →
全部落 anonymous 共享桶（ENABLE_AUTH=1 即跨用户泄漏）。本模块把 impl 收为单源：
  - mcp_server 九件 = 薄包装（HTTP MCP 面，fail-closed：runtime 未置位即抛）；
  - tupu_deepagent 装配面九件 = 进程内 twin（本模块构建——endpoint 已置位 runtime，
    langchain-core 1.5.2 run_in_executor=copy_context().run，executor 线程可读）。
铁律①不变：参数一律不含 user_id（user 由运行时严格解析，绝不进模型可见参数面）。
"""
import json as _json
from typing import Callable, Dict, List


def _impl_fsrs_due(user: str, kind: str = "") -> str:
    from app.services.learning.service import due_cards
    items = due_cards(user, kind=kind or None)
    return _json.dumps({"count": len(items), "items": items}, ensure_ascii=False, default=str)


def _impl_fsrs_review(user: str, item_id: str, rating: int, kind: str = "mother_question",
                      now: float | None = None) -> str:
    from app.services.learning.service import review_card
    try:
        out = review_card(user, kind, item_id, int(rating), now=now)
    except ValueError as e:
        return _json.dumps({"error": str(e)}, ensure_ascii=False)
    return _json.dumps({"next_interval_days": out["interval_days"],
                        "next_due_stability": out["stability"],
                        "reps": out["reps"], "lapses": out["lapses"]}, ensure_ascii=False)


def _impl_mastery_query(user: str, knowledge_point_id: str) -> str:
    from app.services.learning.service import mastery_query
    return _json.dumps(mastery_query(user, knowledge_point_id),
                       ensure_ascii=False, default=str)


def _impl_grade_answer(user: str, question: str, user_answer: str,
                       expected_answer: str = "", rubric: str = "") -> str:
    from app.services.learning.tutor_llm import grade_answer_llm
    return _json.dumps(grade_answer_llm(question, user_answer, expected_answer, rubric),
                       ensure_ascii=False)


def _impl_generate_practice(user: str, knowledge_point_id: str, band: str = "基础") -> str:
    from app.services.learning.tutor_llm import generate_practice_llm
    return _json.dumps(generate_practice_llm(knowledge_point_id, band), ensure_ascii=False)


def _impl_select_exercises(user: str, knowledge_point_id: str, n: int = 5, band: str = "") -> str:
    from app.services.learning.tutor_select import select_exercises_with_neighbors
    return _json.dumps(select_exercises_with_neighbors(
        user, knowledge_point_id, n=n, band=band or None), ensure_ascii=False)


def _impl_wrong_question_add(user: str, variant_text: str, mother_question_id: str = "",
                             error_context: str = "") -> str:
    from app.services.learning.learning_dao import wrong_question_add
    wq_id = wrong_question_add(user, variant_text, mother_question_id, error_context)
    return _json.dumps({"wq_id": wq_id}, ensure_ascii=False)


def _impl_wrong_question_query(user: str, status: str = "", limit: int = 20) -> str:
    from app.services.learning.learning_dao import wrong_question_query
    items = wrong_question_query(user, status=status or "", limit=int(limit or 20))
    return _json.dumps({"count": len(items), "items": items}, ensure_ascii=False, default=str)


def _impl_export_wrong_book(user: str, format: str = "md") -> str:
    from app.services.learning.tutor_export import export_wrong_book_file
    return _json.dumps(export_wrong_book_file(user, format), ensure_ascii=False)


# 单源规格表：name/description（逐字沿 mcp_server 现行 docstring，cleandoc 形）/impl
# 拷贝源纪律（🟢 加固，二次验收 2026-09-15）：SPECS 的 description 以 mcp_server.py 现文件
# 九件 docstring 为唯一拷贝源（迁移时逐字复制），**不许手抄计划文本**——描述漂移即模型行为变。
SPECS: List[Dict[str, object]] = [
    {"name": "fsrs_due",
     "description": "到期复习清单（due<=now 按 due 升序，含 stability/reps）——读面。",
     "impl": _impl_fsrs_due},
    {"name": "fsrs_review",
     "description": "提交复习评分(1-4)→FSRS 调度→落卡+流水（engine 直写——算出来的不许模型编）。\n"
                    "⑤b 铁律①：参数不含 user_id（从 memory_runtime ContextVar 取）；铁律②：now 可注入\n"
                    "（测试不 sleep；fastmcp 禁下划线参数——spec 的 _now 更名 now，语义不变）。",
     "impl": _impl_fsrs_review},
    {"name": "mastery_query",
     "description": "查知识点掌握度+复习史统计（读面）——学情画像与选题权重的数据源。",
     "impl": _impl_mastery_query},
    {"name": "grade_answer",
     "description": "判分（LLM 臂）：对照预期答案/评分要点给分值+逐条评语（判分必走本工具不自评）。",
     "impl": _impl_grade_answer},
    {"name": "generate_practice",
     "description": "生成变式练习题（LLM 臂）：band ∈ 基础|提高|挑战；返回题干+参考答案。",
     "impl": _impl_generate_practice},
    {"name": "select_exercises",
     "description": "选题+图谱邻居扩展：本知识点+前置/后继知识点入选题池（⑤b 唯一新算法语义）\n"
                    "→母题按掌握度加权（掌握度低→权高）→top-n（含变式计数）。",
     "impl": _impl_select_exercises},
    {"name": "wrong_question_add",
     "description": "错题入库（engine 写臂）：判分错误后登记变式题。返回 wq_id。",
     "impl": _impl_wrong_question_add},
    {"name": "wrong_question_query",
     "description": "错题列表（读面）：status ∈ open|resolved|空（全部）。仅本人错题。",
     "impl": _impl_wrong_question_query},
    {"name": "export_wrong_book",
     "description": "导出错题本（engine 臂）：落文件返回 result_ref（tab_export 纪律——大对象不进对话）。",
     "impl": _impl_export_wrong_book},
]


def build_inprocess_tutor_tools() -> list:
    """进程内 twin：签名与 mcp_server 面同名同型（schema 由类型注解推导），
    user 在调用时经 current_user_strict() 严格解析（fail-closed）。"""
    from langchain_core.tools import StructuredTool
    from app.services.memory_runtime import current_user_strict
    tools = []
    for spec in SPECS:
        impl: Callable = spec["impl"]

        def _mk(f: Callable):
            def _run(*args, **kwargs):
                return f(current_user_strict(), *args, **kwargs)
            # P1（计划审查 2026-09-15）：裸 (*args, **kwargs) 无类型注解 → StructuredTool
            # 按 inspect 推导出**空 schema**（模型面九件参数全消失）。挂真实签名+注解双面：
            # inspect.signature 尊重 __signature__；但 pydantic validate_arguments 走
            # get_type_hints（读 __annotations__，不尊重 __signature__）——两面都须挂，
            # 剥 user 首参后 schema 与 MCP 面等价，「零感知」承诺才成立。
            import inspect as _inspect
            _sig = _inspect.signature(f)
            _params = list(_sig.parameters.values())[1:]  # 去 user 首参，余参带注解
            _run.__signature__ = _sig.replace(parameters=_params)
            _run.__annotations__ = {p.name: p.annotation for p in _params
                                    if p.annotation is not _inspect.Parameter.empty}
            # I-1（复审 2026-09-15）：单源一致性锁——两面同源于 _params，若未来有人只改
            # 其一（漏注解/漏签名）装配期立即炸出，不再表现为工具面莫名回退。
            assert set(_run.__annotations__) == {p.name for p in _params}, \
                f"{spec['name']}: 签名/注解双源漂移（I-1）" \
                f" annotations={sorted(_run.__annotations__)}" \
                f" params={sorted(p.name for p in _params)}"
            _run.__name__ = str(spec["name"])
            _run.__doc__ = str(spec["description"])
            return _run

        tools.append(StructuredTool.from_function(
            func=_mk(impl), name=str(spec["name"]), description=str(spec["description"])))
    return tools
