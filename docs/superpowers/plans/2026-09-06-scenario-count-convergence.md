# 场景 COUNT 题直通收敛 实现计划（批16-A）

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 场景 COUNT 题「统计重过载台区数量」从 136~200s 收敛到 ≤15s（直通级），判定表输出与批14-A 验收逐字一致，generic 直通/明细题零回归。

**架构：** 复用批9 直通管道（`direct_pipeline.py`）——金标种子提供「已验证 SQL 单源」（数据前置），`evaluate_direct_eligibility` 路由门从 generic-only 放开到 scenario（一处条件改动），安全链四件套（来源可信/validate_safe_sql/模板渲染/失败回退 Agent）全部不变。

**技术栈：** FastAPI + SQLAlchemy（金标 CRUD 现成）+ Qdrant（tupu_golden_qa 同步内置）+ pytest + Playwright headless 串行 e2e（AGENTS.md 铁律）。

**规格来源：** `docs/superpowers/specs/2026-09-06-scenario-count-convergence-design.md`（本计划实现其 §五；§六闸后项与 §七交接项在任务5 收口）。

**纪律（AGENTS.md）：** 后端 28000（`backend/__start_8000.py`，重启必设 `PYTHONUTF8=1`）；e2e 一律 Playwright headless **串行**；每任务独立 commit；主文档登记由实施会话执行。

---

## 文件结构

| 文件 | 操作 | 职责 |
|---|---|---|
| `docs/批16取证记录_20260906.md` | 创建 | 方案零取证基线（现状耗时分解，决策留档） |
| `backend/scripts/_seed_16a.py` | 创建 | 金标种子：场景 COUNT 题已验证问答对入库（幂等+自查） |
| `backend/app/services/direct_pipeline.py` | 修改 L39（一处条件） | 直通资格路由门放开 scenario |
| `backend/tests/test_16a.py` | 创建 | 直通资格七测（含前置 sanity） |
| 主文档 `docs/问数智能体vNext最终设计文档_实施定稿_20260824.md` | 修改（任务5） | 批16-A 状态登记（实施会话按批14/15 惯例） |

---

### 任务 1：取证基线（方案零，0 新代码）

**文件：**
- 创建：`docs/批16取证记录_20260906.md`
- 只读使用：`backend/scripts/_diag_timing.py`（现成逐轮计时诊断）

- [ ] **步骤 1.1：重启后端（PYTHONUTF8=1 纪律）**

```powershell
$env:PYTHONUTF8 = '1'
# 停掉 28000 旧进程后：
python backend/__start_8000.py   # 后台运行
```

- [ ] **步骤 1.2：跑逐轮计时诊断**

```powershell
python -u backend/scripts/_diag_timing.py "统计重过载台区数量"
```

预期：输出该题逐轮事件计时（定位慢在哪一轮）；同时后端日志出现 `[PrepTiming]` 行（lock/state/route/rewrite/retrieval 五段毫秒）。

- [ ] **步骤 1.3：记录基线到取证记录**

创建 `docs/批16取证记录_20260906.md`，按下表如实填数（数字以实测为准，本计划不预设结论）：

```markdown
# 批16-A 取证基线（2026-09-06）

## 现状耗时分解：「统计重过载台区数量」
| 段 | 毫秒（实测） | 占比 |
|---|---|---|
| prep 五段合计（lock+state+route+rewrite+retrieval） |  |  |
| Agent 轮数 × 每轮延迟（_diag_timing 逐轮） |  |  |
| total（done 载荷 timing.total） |  |  |

## 判定
- [ ] 定位轮是否爆量（是 → 触发 spec §六「方案三」闸后备选；否 → 方案二主线继续）
```

- [ ] **步骤 1.4：Commit**

```powershell
git add docs/批16取证记录_20260906.md
git commit -m "批16-A 取证基线：场景COUNT题现状耗时分解（诊断留档）"
```

---

### 任务 2：金标种子（方案一，数据前置）

**文件：**
- 创建：`backend/scripts/_seed_16a.py`

- [ ] **步骤 2.1：编写种子脚本**

```python
# -*- coding: utf-8 -*-
"""_seed_16a.py - 批16-A 金标种子：场景 COUNT 题已验证问答对入库（幂等）。

SQL 单源：MetricQueryLog 该题最近一次成功执行的 executed_sql（14-A e2e 已验证
出表 重过载台区数/过载台区数/重载台区数/判定台区总数 = 2/1/1/2）。
列名实据：golden_qa_service.seed_golden L228-232 的抽样过滤。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.base import KgGoldenQaSet, MetricQueryLog
from app.services.golden_qa_service import add_golden, search_golden_qa

QUESTION = "统计重过载台区数量"


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(KgGoldenQaSet).filter(KgGoldenQaSet.question == QUESTION).first():
            print(f"[skip] 金标已存在: {QUESTION}")
        else:
            row = (db.query(MetricQueryLog)
                     .filter(MetricQueryLog.query_status == "success",
                             MetricQueryLog.user_query == QUESTION,
                             MetricQueryLog.executed_sql.isnot(None))
                     .order_by(MetricQueryLog.created_at.desc())
                     .first())
            if row is None:
                sys.exit("[fail] MetricQueryLog 无该题成功记录——先跑一轮 14-A e2e 再种子")
            out = add_golden(db, question=QUESTION, expected_sql=row.executed_sql,
                             route_type="scenario", scenario_tag="distribution-overload")
            print(f"[seed] ok={out.get('ok')} id={out.get('id')}")
        hits = search_golden_qa(db, QUESTION)
        print(f"[verify] top={[(h.get('score'), h.get('question')) for h in hits[:2]]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2.2：运行种子脚本**

```powershell
python backend/scripts/_seed_16a.py
```

预期输出两行：`[seed] ok=True id=<uuid>`（或 `[skip]`）与 `[verify] top=[(1.0, '统计重过载台区数量')]`——**score=1.0 即 Tier1 确定性命中（计数同义归一化 数量→总数）**。若 `[verify]` 无 1.0 命中，停下排查 Qdrant 同步（`_sync_golden_qdrant` 日志）再继续。

- [ ] **步骤 2.3：Commit**

```powershell
git add backend/scripts/_seed_16a.py
git commit -m "批16-A 金标种子脚本：场景COUNT题已验证问答对入库（幂等+Tier1自查）"
```

---

### 任务 3：直通资格放开（方案二，TDD）

**文件：**
- 修改：`backend/app/services/direct_pipeline.py:39`
- 测试：`backend/tests/test_16a.py`

- [ ] **步骤 3.1：编写失败的测试**

创建 `backend/tests/test_16a.py`：

```python
# -*- coding: utf-8 -*-
"""批16-A 单测：场景 COUNT 题直通资格放开（spec §五.2）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.direct_pipeline import evaluate_direct_eligibility
from app.services.intent_classifier import has_dynamic_condition, is_count_intent


class _Contract:
    """最小契约桩：evaluate_direct_eligibility 只读这四个属性。"""

    def __init__(self, route_type="generic", hits=None, clarify=False):
        self.route_type = route_type
        self.clarify_required = clarify
        self._runtime = {"golden_hits": hits or []}


def _hit(score=1.0, sql="SELECT COUNT(*) AS n FROM t LIMIT 1", engine="doris"):
    return {"score": score, "sql": sql, "engine": engine}


Q_COUNT_SCENARIO = "统计重过载台区数量"
Q_DETAIL_SCENARIO = "哪些台区重过载"               # 无计数词 -> 非 count 意图
Q_COUNT_DYN = "重过载台区数量超过10个的有多少"     # 带比较词 -> 动态条件


def test_sanity_intent_and_condition_words():
    """前置 sanity：测试措辞与词表实际对齐（脱节则在此处炸，不误判主断言）。"""
    assert is_count_intent(Q_COUNT_SCENARIO)
    assert not is_count_intent(Q_DETAIL_SCENARIO)
    assert has_dynamic_condition(Q_COUNT_DYN)


def test_scenario_count_eligible():
    """核心：scenario 路由 + 金标>=0.95 + count 意图 + 无动态条件 -> 可直通。"""
    plan = evaluate_direct_eligibility(_Contract("scenario", [_hit()]), Q_COUNT_SCENARIO)
    assert plan is not None
    assert plan["engine"] == "doris"
    assert plan["sql"].startswith("SELECT")


def test_scenario_non_count_still_agent():
    assert evaluate_direct_eligibility(_Contract("scenario", [_hit()]), Q_DETAIL_SCENARIO) is None


def test_scenario_dynamic_condition_still_agent():
    assert evaluate_direct_eligibility(_Contract("scenario", [_hit()]), Q_COUNT_DYN) is None


def test_scenario_low_sim_still_agent():
    assert evaluate_direct_eligibility(
        _Contract("scenario", [_hit(score=0.90)]), Q_COUNT_SCENARIO) is None


def test_clarify_blocks_direct():
    assert evaluate_direct_eligibility(
        _Contract("scenario", [_hit()], clarify=True), Q_COUNT_SCENARIO) is None


def test_generic_unchanged():
    assert evaluate_direct_eligibility(
        _Contract("generic", [_hit()]), "统计用电客户总数") is not None
```

- [ ] **步骤 3.2：运行测试验证失败**

```powershell
python -m pytest backend/tests/test_16a.py -v
```

预期：**FAIL**——`test_scenario_count_eligible` 等 4 个 scenario 用例断言 `plan is not None` 失败（现行 L39 路由门对 scenario 返回 None）；`test_sanity_*` 与 `test_generic_unchanged` 应已 PASS。

- [ ] **步骤 3.3：最小实现（一处条件改动）**

`backend/app/services/direct_pipeline.py` L39：

```python
# 改前：
    if contract is None or getattr(contract, "route_type", "") != "generic":
# 改后：
    # 批16-A：场景 COUNT 题放开直通资格（spec §四方案二）——安全链不变
    # （来源可信 enabled 已验证 SQL + validate_safe_sql + 失败回退 Agent）；
    # 场景金标 SQL 单源 = MetricQueryLog 已成功执行记录（14-A e2e 出表 2/1/1/2）。
    if contract is None or getattr(contract, "route_type", "") not in ("generic", "scenario"):
```

- [ ] **步骤 3.4：运行测试验证通过**

```powershell
python -m pytest backend/tests/test_16a.py -v
```

预期：**7 passed**。

- [ ] **步骤 3.5：全量回归**

```powershell
python -m pytest backend/tests -q
```

预期：**687 passed**（680 基线 + 本批 7），warnings 不增（基线 35）。

- [ ] **步骤 3.6：Commit**

```powershell
git add backend/app/services/direct_pipeline.py backend/tests/test_16a.py
git commit -m "批16-A 直通资格放开：scenario路由COUNT题可直通（路由门一处条件+七测，安全链不变）"
```

---

### 任务 4：e2e 验收（Playwright 串行，AGENTS.md 铁律）

**文件：**
- 只读使用：`backend/scripts/_pw_e2e.py`（现成入口）

- [ ] **步骤 4.1：重启后端（PYTHONUTF8=1）**

同任务1 步骤 1.1。

- [ ] **步骤 4.2：主验收——COUNT 题直通**

```powershell
python -u backend/scripts/_pw_e2e.py "统计重过载台区数量" 16a_count 120
```

预期：判定表表头 4 列（重过载台区数/过载台区数/重载台区数/判定台区总数）、首行 2/1/1/2、**端到端 ≤15s**（日志 `[DirectPipeline] 直通完成: sim=1.00 ...`）；截图产出 `_pw_16a_count.png`（路径以脚本 stdout 打印为准）。

- [ ] **步骤 4.3：回归一——generic 直通不变**

```powershell
python -u backend/scripts/_pw_e2e.py "统计用电客户总数" 16a_generic 60
```

预期：秒级出数，行为与批15 基线一致。

- [ ] **步骤 4.4：回归二——明细题走 Agent 不变**

```powershell
python -u backend/scripts/_pw_e2e.py "哪些台区重过载" 16a_detail 240
```

预期：走完整 Agent 路径出明细表（不被直通误伤——`is_count_intent` 对该问法为 False）。

- [ ] **步骤 4.5：截图留档 + Commit**

```powershell
git add "*_pw_16a_*.png"
git commit -m "批16-A e2e 验收：COUNT题直通≤15s出表一致 + generic/明细双回归（截图留档）"
```

---

### 任务 5：主文档登记 + 交接收口 + 决策点

- [ ] **步骤 5.1：主文档登记批16-A**（按批14/15 惯例，状态表一行 + 完成行，commit）

- [ ] **步骤 5.2：提交交接欠账三件**（spec §七）

```powershell
git add docs/设计初衷还原_为什么用deepagents与能力使用全景_20260906.md AGENTS.md docs/superpowers/specs/2026-09-06-scenario-count-convergence-design.md docs/superpowers/plans/2026-09-06-scenario-count-convergence.md
git commit -m "批16-A 交接收口：设计初衷还原存档+设计窗口规划纪律(AGENTS.md)+spec/plan入库"
```

- [ ] **步骤 5.3：决策点——COUNT 措辞变体覆盖评估（串行三轮）**

```powershell
python -u backend/scripts/_pw_e2e.py "重过载台区有多少个" 16a_v1 120
python -u backend/scripts/_pw_e2e.py "重过载的台区数目" 16a_v2 120
python -u backend/scripts/_pw_e2e.py "数一下重过载台区" 16a_v3 120
```

判定（spec §八.4）：
- **三轮全部直通（≤15s）且出表一致** → 类级覆盖达标，批16-A 收口，主文档补记一行变体结论；
- **任一轮未直通**（Tier2 相似度 <0.95 走了 Agent）→ 不现场扩，主文档登记「COUNT 变体专项」为闸后项（触发条件：变体题高频出现），回设计窗口按两技能流程另出 spec。

- [ ] **步骤 5.4：最终 Commit（若 5.3 有补记）**

```powershell
git add docs/问数智能体vNext最终设计文档_实施定稿_20260824.md
git commit -m "批16-A 主文档登记：场景COUNT直通收敛落地+变体覆盖决策结论"
```
