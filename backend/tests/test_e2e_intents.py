"""端到端意图路由验证脚本

模拟前端 SSE 调用，验证 10 种技能的代表问句能被正确路由。
不依赖数据库/LLM，只验证 classify_intent + generate_plan 缓存命中。

运行方式：
    cd backend
    python -m tests.test_e2e_intents
"""
import asyncio
import sys
from pathlib import Path

# 确保 backend 在 sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.skill_router import classify_intent, needs_sql, get_skill_category
from app.services.plan_execute import generate_plan, _plan_cache


# 10 种技能的代表问句
TEST_CASES = [
    # 问数类（需 SQL）
    ("查用电客户的户号", "basic-query", "基础查询-单表"),
    ("用电客户的名称、联系电话、证件号码", "multi-hop-query", "多表关联-跨实体字段升级"),
    ("统计各用电客户的数量", "aggregate-query", "聚合统计-GROUP BY"),
    ("用电量最大的前10个客户", "topn-query", "排名-ORDER BY+LIMIT"),
    ("查 dim_customer 表", "direct-query", "直接查表-跳过定位"),
    # 知识类（不碰 SQL）
    ("什么是变压器", "explain-concept", "概念解释"),
    ("用电客户有哪些属性", "explore-graph", "图谱探索"),
    ("联系电话在哪个表", "find-entity", "实体查找"),
    ("用电客户的空值情况", "data-quality", "数据质量"),
    ("用电客户数据从哪来", "trace-lineage", "数据血缘"),
    # 续轮
    ("执行", "execute-sql", "续轮-执行SQL", True),  # has_context=True
]


async def run_e2e_test():
    print("=" * 80)
    print("端到端意图路由验证")
    print("=" * 80)

    passed = 0
    failed = 0
    issues = []

    for case in TEST_CASES:
        if len(case) == 3:
            query, expected_skill, desc = case
            has_context = False
        else:
            query, expected_skill, desc, has_context = case

        print(f"\n[测试] {desc}")
        print(f"  问句: {query}")
        print(f"  期望: {expected_skill}")

        # Step 1: 意图分类
        actual_skill = classify_intent(query, has_context=has_context)
        if actual_skill == expected_skill:
            print(f"  ✅ 路由正确: {actual_skill}")
        else:
            print(f"  ❌ 路由错误: 期望 {expected_skill}, 实际 {actual_skill}")
            failed += 1
            issues.append({
                "type": "路由错误",
                "query": query,
                "expected": expected_skill,
                "actual": actual_skill,
                "desc": desc,
            })
            continue

        # Step 2: 验证技能分类
        category = get_skill_category(actual_skill)
        is_needs_sql = needs_sql(actual_skill)
        print(f"  分类: {category}, 需SQL: {is_needs_sql}")

        # Step 3: 验证计划缓存命中（execute-sql 除外，它不进 plan_cache）
        if actual_skill != "execute-sql":
            try:
                plan = await generate_plan(query, actual_skill, context=None)
                step_count = len(plan.steps)
                step_names = [s.action for s in plan.steps]
                print(f"  ✅ 计划生成: {step_count} 步")
                print(f"     步骤: {' → '.join(step_names)}")

                # 验证步骤数符合预期
                expected_steps = {
                    "basic-query": 7,
                    "multi-hop-query": 7,
                    "aggregate-query": 7,
                    "topn-query": 7,
                    "direct-query": 2,
                    "explain-concept": 1,
                    "explore-graph": 2,
                    "find-entity": 1,
                    "data-quality": 7,
                    "trace-lineage": 2,
                }
                if actual_skill in expected_steps:
                    expected_count = expected_steps[actual_skill]
                    if step_count != expected_count:
                        print(f"  ⚠️  步骤数异常: 期望 {expected_count}, 实际 {step_count}")
                        issues.append({
                            "type": "步骤数异常",
                            "query": query,
                            "skill": actual_skill,
                            "expected_steps": expected_count,
                            "actual_steps": step_count,
                            "desc": desc,
                        })
            except Exception as e:
                print(f"  ❌ 计划生成失败: {e}")
                failed += 1
                issues.append({
                    "type": "计划生成失败",
                    "query": query,
                    "skill": actual_skill,
                    "error": str(e),
                    "desc": desc,
                })
                continue

        # Step 4: 验证 user_input 注入（问数类）
        if is_needs_sql and actual_skill != "execute-sql":
            try:
                plan = await generate_plan(query, actual_skill, context=None)
                # 检查第一步是否含 {{step0.user_input}}（应已被替换）
                first_step = plan.steps[0]
                if "{{step0.user_input}}" in first_step.params_template:
                    print(f"  ❌ user_input 未注入: 仍含占位符")
                    failed += 1
                    issues.append({
                        "type": "user_input未注入",
                        "query": query,
                        "skill": actual_skill,
                        "desc": desc,
                    })
                else:
                    print(f"  ✅ user_input 已注入")
            except Exception as e:
                print(f"  ❌ user_input 注入检查失败: {e}")

        passed += 1

    # 汇总
    print("\n" + "=" * 80)
    print(f"测试汇总: {passed} 通过, {failed} 失败, 共 {len(TEST_CASES)} 个用例")
    print("=" * 80)

    if issues:
        print("\n问题清单:")
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. [{issue['type']}] {issue.get('desc', '')}")
            print(f"   问句: {issue.get('query', '')}")
            if "expected" in issue:
                print(f"   期望: {issue['expected']}, 实际: {issue['actual']}")
            if "error" in issue:
                print(f"   错误: {issue['error']}")
            if "expected_steps" in issue:
                print(f"   期望步骤数: {issue['expected_steps']}, 实际: {issue['actual_steps']}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_e2e_test())
    sys.exit(0 if success else 1)
