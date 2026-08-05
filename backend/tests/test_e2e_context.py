"""多轮上下文优化验证

验证当 confirmed 已锁定 L2 + 实体时，generate_plan 跳过前 4 步定位，
端到端从 7 步降到 3 步。
"""
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.plan_execute import generate_plan


async def run_context_test():
    print("=" * 80)
    print("多轮上下文优化验证")
    print("=" * 80)

    # 模拟第一轮已锁定 L2 + 实体的上下文
    context = {
        "confirmed": {
            "L2": "用电客户",
            "L2_id": "l2-uuid-123",
            "L2X": "dim_customer",
            "entity_code": "dim_customer",
            "attributes": [
                {"attribute_name": "客户名称", "attribute_code": "cust_name"},
            ],
        }
    }

    issues = []

    # 测试 basic-query 多轮优化
    print("\n[测试] basic-query 多轮优化")
    plan = await generate_plan("查用电客户的户号", "basic-query", context=context)
    step_count = len(plan.steps)
    step_names = [s.action for s in plan.steps]
    print(f"  步骤数: {step_count}")
    print(f"  步骤: {' → '.join(step_names)}")

    if step_count == 3:
        print(f"  ✅ 多轮优化生效: 7 步 → 3 步")
        # 验证跳过了 fetch_l1_l2_tree / validate_l2 / fetch_subgraph / validate_attributes
        if "fetch_l1_l2_tree" in step_names:
            print(f"  ❌ 仍含 fetch_l1_l2_tree，未正确跳过定位步骤")
            issues.append("basic-query 多轮优化: 仍含 fetch_l1_l2_tree")
        else:
            print(f"  ✅ 已跳过定位步骤")
    else:
        print(f"  ❌ 多轮优化未生效: 期望 3 步, 实际 {step_count} 步")
        issues.append(f"basic-query 多轮优化: 期望 3 步, 实际 {step_count} 步")

    # 测试无上下文时仍为 7 步
    print("\n[测试] 无上下文时保持 7 步")
    plan_no_ctx = await generate_plan("查用电客户的户号", "basic-query", context=None)
    step_count_no_ctx = len(plan_no_ctx.steps)
    print(f"  步骤数: {step_count_no_ctx}")
    if step_count_no_ctx == 7:
        print(f"  ✅ 无上下文时保持 7 步")
    else:
        print(f"  ❌ 无上下文时步骤数异常: 期望 7, 实际 {step_count_no_ctx}")
        issues.append(f"无上下文步骤数: 期望 7, 实际 {step_count_no_ctx}")

    # 测试 context 无 confirmed 时仍为 7 步
    print("\n[测试] context 无 confirmed 时保持 7 步")
    plan_empty_ctx = await generate_plan("查用电客户", "basic-query", context={})
    step_count_empty = len(plan_empty_ctx.steps)
    if step_count_empty == 7:
        print(f"  ✅ context 无 confirmed 时保持 7 步")
    else:
        print(f"  ❌ 步骤数异常: 期望 7, 实际 {step_count_empty}")
        issues.append(f"context 无 confirmed: 期望 7, 实际 {step_count_empty}")

    # 测试 confirmed 缺 L2X 时保持 7 步（不满足跳过条件）
    print("\n[测试] confirmed 缺 L2X 时保持 7 步")
    plan_no_l2x = await generate_plan("查用电客户", "basic-query", context={"confirmed": {"L2_id": "x"}})
    step_count_no_l2x = len(plan_no_l2x.steps)
    if step_count_no_l2x == 7:
        print(f"  ✅ 缺 L2X 时保持 7 步")
    else:
        print(f"  ❌ 步骤数异常: 期望 7, 实际 {step_count_no_l2x}")
        issues.append(f"缺 L2X: 期望 7, 实际 {step_count_no_l2x}")

    # 汇总
    print("\n" + "=" * 80)
    if issues:
        print(f"发现问题 {len(issues)} 个:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ 多轮上下文优化全部通过")
    print("=" * 80)

    return len(issues) == 0


if __name__ == "__main__":
    success = asyncio.run(run_context_test())
    sys.exit(0 if success else 1)
