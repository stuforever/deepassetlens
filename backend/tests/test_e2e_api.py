"""后端 API 端到端测试脚本

直接调用后端 SSE 流式 API，测试 10 种技能的代表问句。
不依赖前端，直接解析 SSE 事件流。

运行方式：
    cd backend
    python -m tests.test_e2e_api
"""
import json
import time
import requests
from typing import Dict, List, Any, Optional

BASE_URL = "http://localhost:8100/api/data-intelligence/chat/deepagent/stream"

# 10 种技能的代表问句
TEST_CASES = [
    {"query": "查用电客户的户号", "expected_skill": "basic-query", "desc": "基础查询"},
    {"query": "用电客户的名称、联系电话、证件号码", "expected_skill": "multi-hop-query", "desc": "多表关联"},
    {"query": "统计各用电客户的数量", "expected_skill": "aggregate-query", "desc": "聚合统计"},
    {"query": "用电量最大的前10个客户", "expected_skill": "topn-query", "desc": "排名TopN"},
    {"query": "查 dim_customer 表", "expected_skill": "direct-query", "desc": "直接查表"},
    {"query": "什么是变压器", "expected_skill": "explain-concept", "desc": "概念解释"},
    {"query": "用电客户有哪些属性", "expected_skill": "explore-graph", "desc": "图谱探索"},
    {"query": "联系电话在哪个表", "expected_skill": "find-entity", "desc": "实体查找"},
    {"query": "用电客户的空值情况", "expected_skill": "data-quality", "desc": "数据质量"},
    {"query": "用电客户数据从哪来", "expected_skill": "trace-lineage", "desc": "数据血缘"},
]


def call_sse(query: str, thread_id: str, timeout: int = 90) -> Dict[str, Any]:
    """调用 SSE 流式 API，解析所有事件"""
    payload = {
        "thread_id": thread_id,
        "user_input": query,
        "format": "card",
        "mode": "question_data",
    }
    events: List[Dict[str, Any]] = []
    final_resp: Optional[Dict] = None
    error: Optional[str] = None
    start_time = time.time()

    try:
        resp = requests.post(
            BASE_URL, json=payload, stream=True, timeout=timeout
        )
        resp.raise_for_status()

        current_event = "message"
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                # 空行表示事件结束
                current_event = "message"
                continue
            if line.startswith("event:"):
                current_event = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str:
                continue
            try:
                data = json.loads(data_str)
                evt = {"event": current_event, "data": data}
                events.append(evt)
                if current_event == "done":
                    final_resp = data
                elif current_event == "error":
                    error = data.get("message", "unknown error") if isinstance(data, dict) else str(data)
            except json.JSONDecodeError:
                pass
    except requests.exceptions.Timeout:
        error = f"请求超时（{timeout}s）"
    except Exception as e:
        error = str(e)

    elapsed = round(time.time() - start_time, 1)

    # 分析事件
    think_steps = [e for e in events if e.get("event") == "think"]
    status_events = [e for e in events if e.get("event") == "status"]
    token_events = [e for e in events if e.get("event") == "token"]
    sql_result_events = [e for e in events if e.get("event") == "sql_result"]
    trace_events = [e for e in events if e.get("event") == "trace"]
    final_events = [e for e in events if e.get("event") == "final"]
    recommend_events = [e for e in events if e.get("event") == "recommend"]

    # 提取关键信息
    has_sql = False
    has_sql_result = False
    has_final_answer = False
    has_recommendations = False
    sql_text = ""
    row_count = 0
    final_answer = ""
    recommendations: List = []
    confirmed: Dict = {}
    detected_skill = ""

    if final_resp:
        confirmed = final_resp.get("confirmed", {})
        has_sql = bool(confirmed.get("assembled_sql"))
        sql_text = confirmed.get("assembled_sql", "")
        has_final_answer = bool(final_resp.get("final_answer"))
        final_answer = (final_resp.get("final_answer") or "")[:200]
        recommendations = final_resp.get("recommendations") or []
        has_recommendations = len(recommendations) > 0
        detected_skill = final_resp.get("routed_skill", "") or final_resp.get("skill_type", "")
        # sql_result 可能在 final_resp 或单独事件
        sql_result = final_resp.get("sql_result")
        if sql_result and sql_result.get("columns"):
            has_sql_result = True
            row_count = sql_result.get("row_count", 0)

    if sql_result_events:
        has_sql_result = True
        row_count = sql_result_events[0].get("data", {}).get("row_count", 0)

    # 从 think 步骤推断技能
    if not detected_skill and think_steps:
        actions = [t.get("data", {}).get("action", "") for t in think_steps]
        if "generate_join_sql" in actions:
            detected_skill = "multi-hop-query"
        elif "search_concepts" in actions:
            detected_skill = "explain-concept"
        elif "search_entities" in actions and "get_entity_relations" in actions:
            detected_skill = "trace-lineage"
        elif "search_entities" in actions:
            detected_skill = "find-entity"
        elif len(actions) == 1 and "search_concepts" in actions:
            detected_skill = "explain-concept"

    return {
        "query": query,
        "elapsed": elapsed,
        "event_count": len(events),
        "think_steps": len(think_steps),
        "think_actions": [t.get("data", {}).get("action", "") for t in think_steps],
        "status_events": len(status_events),
        "token_events": len(token_events),
        "has_sql": has_sql,
        "sql_text": sql_text[:200] if sql_text else "",
        "has_sql_result": has_sql_result,
        "row_count": row_count,
        "has_final_answer": has_final_answer,
        "final_answer_preview": final_answer,
        "has_recommendations": has_recommendations,
        "recommendations_count": len(recommendations),
        "confirmed_keys": list(confirmed.keys()) if confirmed else [],
        "detected_skill": detected_skill,
        "error": error,
        "has_done": final_resp is not None,
    }


def run_tests():
    print("=" * 90)
    print("后端 API 端到端测试 - 10 种技能代表问句")
    print("=" * 90)

    results = []
    passed = 0
    failed = 0
    errors = 0

    for i, case in enumerate(TEST_CASES, 1):
        query = case["query"]
        expected = case["expected_skill"]
        desc = case["desc"]
        thread_id = f"e2e_test_{i}_{int(time.time())}"

        print(f"\n[{i}/{len(TEST_CASES)}] {desc}")
        print(f"  问句: {query}")
        print(f"  期望技能: {expected}")

        result = call_sse(query, thread_id)
        result["expected_skill"] = expected
        result["desc"] = desc
        results.append(result)

        # 输出结果
        if result["error"]:
            print(f"  ❌ 错误: {result['error']}")
            errors += 1
        elif not result["has_done"]:
            print(f"  ❌ 未收到 done 事件（流异常结束）")
            errors += 1
        else:
            print(f"  ✅ 完成（{result['elapsed']}s, {result['event_count']} 事件）")
            print(f"     推理步骤: {result['think_steps']} 步")
            print(f"     步骤动作: {' → '.join(result['think_actions'])}")
            print(f"     生成SQL: {'是' if result['has_sql'] else '否'}")
            if result["sql_text"]:
                print(f"     SQL预览: {result['sql_text'][:100]}...")
            print(f"     查询结果: {'是' if result['has_sql_result'] else '否'}" +
                  (f" ({result['row_count']} 行)" if result['has_sql_result'] else ""))
            print(f"     最终答案: {'是' if result['has_final_answer'] else '否'}")
            if result["final_answer_preview"]:
                print(f"     答案预览: {result['final_answer_preview'][:100]}...")
            print(f"     推荐问题: {result['recommendations_count']} 个")
            print(f"     confirmed: {result['confirmed_keys']}")

            # 验证技能匹配
            detected = result["detected_skill"]
            if detected and detected == expected:
                print(f"  ✅ 技能匹配: {detected}")
                passed += 1
            elif detected:
                print(f"  ⚠️  技能不匹配: 期望 {expected}, 实际 {detected}")
                failed += 1
            else:
                print(f"  ⚠️  无法确定技能（无 skill_type 字段）")
                failed += 1

    # 汇总
    print("\n" + "=" * 90)
    print(f"测试汇总: {passed} 通过, {failed} 不匹配, {errors} 错误, 共 {len(TEST_CASES)} 个用例")
    print("=" * 90)

    # 问题清单
    issues = []
    for r in results:
        if r["error"]:
            issues.append(f"  ❌ [{r['desc']}] 错误: {r['error']}")
        elif not r["has_done"]:
            issues.append(f"  ❌ [{r['desc']}] 未收到 done 事件")
        elif r["detected_skill"] and r["detected_skill"] != r["expected_skill"]:
            issues.append(f"  ⚠️  [{r['desc']}] 技能不匹配: 期望 {r['expected_skill']}, 实际 {r['detected_skill']}")
        if r["has_sql"] and not r["has_sql_result"] and r["expected_skill"] not in ("explain-concept", "explore-graph", "find-entity", "trace-lineage"):
            issues.append(f"  ⚠️  [{r['desc']}] 生成了SQL但未执行")
        if not r["has_final_answer"] and not r["error"]:
            issues.append(f"  ⚠️  [{r['desc']}] 无最终答案")

    if issues:
        print("\n问题清单:")
        for issue in issues:
            print(issue)
    else:
        print("\n✅ 所有问题测试通过")

    # 详细结果表
    print("\n" + "=" * 90)
    print("详细结果表")
    print("=" * 90)
    print(f"{'#':<3} {'描述':<12} {'问句':<30} {'期望技能':<20} {'实际技能':<20} {'步骤':<5} {'SQL':<5} {'结果':<5} {'答案':<5} {'耗时':<6} {'状态':<6}")
    print("-" * 130)
    for i, r in enumerate(results, 1):
        status = "❌" if r["error"] else ("✅" if r["has_done"] else "❌")
        print(f"{i:<3} {r['desc']:<12} {r['query'][:28]:<30} {r['expected_skill']:<20} {r['detected_skill'] or '?':<20} {r['think_steps']:<5} {'是' if r['has_sql'] else '否':<5} {'是' if r['has_sql_result'] else '否':<5} {'是' if r['has_final_answer'] else '否':<5} {r['elapsed']:<6} {status:<6}")

    return errors == 0 and failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
