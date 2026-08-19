# 受控 Skill 问答平台 v2 —— 上线前检查清单

> 对应：《受控问答平台提升设计_20260818.md》（设计）+《受控Skill问答平台v2_改动报告_20260818.md》（实施）
> 用途：上线审核逐项勾选；任一「必查」不通过即不得发布。
> 状态：批1/2/3 + 批4（生产治理）已实施；剩余项（场景迁移 / 运行观测台 / 模板指纹）已全部完成；**专家评审 2×P0 + 6×P1 + 观测台小事已全部修复（2026-08-19，pytest 305 passed）；专家二轮三项强制修改已全部落地（2026-08-19，pytest 311 passed：完整 AST 严格模板 / 多引擎按 required_entity 终止 / template.bound+drift 真派发 + context.contract + template_mode 枚举 + 前端折叠与事件累积）**。本文档为运维/审核侧动作清单。

---

## A. 必查（阻断项，任一不通过不得上线）

| # | 检查项 | 方式 | 通过标准 |
|---|---|---|---|
| A1 | 后端全量测试 | `python -m pytest -q`（backend/） | 全绿（二轮修复后基线 311 passed / 6 deselected） |
| A2 | 前端编译 | `npx tsc --noEmit`（改动文件） | 0 错误（既有 `__tests__` Jest 全局基线除外） |
| A3 | 治理端点可用 | `GET /api/data-intelligence/skills/catalog`、`/skills/metrics` | 均 `ok=true` |
| A4 | 技能目录状态 | catalog 快照 | `distribution-overload` enabled=true；`project-lifecycle-cost` enabled=true（multi_engine=true，forbid_md=false）；无 x_tupu 的旧技能明确 disabled + 告警（渐进迁移） |
| A5 | 路由判定唯一 | `POST /skills/simulate-route` 「所有用电户与配变户变关系」 | `scenario / distribution-overload / relationship` |
| A6 | 契约完整 | simulate-route 返回 contract | allowed/forbidden/template_ids/scope/stop_when/output_mode 字段齐全 |
| A7 | 受控铁律抽查 | acceptance 基线 | `test_acceptance_v2.py` 全绿（12 条验收） |
| A8 | 服务状态 | 28000 后端 / 23000 前端 | 均 200 |

## B. 建议查（治理/审核）

| # | 检查项 | 方式 | 说明 |
|---|---|---|---|
| B1 | 审计轨迹 | `GET /skills/metrics` → `audit` | 上线后应有 route.scenario / engine.selected / stop.reached / policy.rejected / template.bound / template.drift 等事件 |
| B2 | 指标健康 | metrics `counters` | rejected_total 不应持续高企（说明模型频繁越权，需查系统提示/模板） |
| B3 | 版本稳定性 | catalog warnings / 后端日志 | 「内容哈希变化但 version 未变」= 未灰度改动，必须 bump version 才允许发布 |
| B4 | 编译期校验 | catalog disabled 列表 | 新 SKILL.md 未通过校验时被禁用并告警，不允许"猜着执行" |
| B5 | 前端五卡回归 | 浏览器冒烟（模拟器 + 真实聊天） | 五张业务卡流式运行中即时渲染，页面无相关报错 |
| B6 | 运行观测台 | 浏览器打开 `/governance` | Skill 目录/指标卡/审计轨迹渲染；多引擎技能显示「多引擎」标签 |
| B7 | 模板指纹 | metrics audit 中 `template.bound`/`template.drift` | 户变关系查询应出现 template.bound（结构一致）；出现 template.drift 时审核模型 SQL 结构 |

## C. 回滚策略（有损回滚，逐个确认）

| 层级 | 回滚动作 | 验证 |
|---|---|---|
| 技能级 | 删除/回退 `SKILL.md`（`git` 手工确认，不自动提交） | catalog 中该技能消失/回到旧版，路由自动落到 generic 低权限只读 |
| 能力级 | 关闭 `x_tupu.enabled=false` | 该技能被目录禁用，不参与路由 |
| 模块级 | 还原 `tupu_deepagent.py` / `data_intelligence.py`（移除 SkillPolicy 装配） | 回到自由问答（受控化前的行为基线） |
| 服务级 | 重启后端（28000） | 配置/代码变更生效 |

> 说明：违规策略已是「首次拒绝+指引、再次终止本轮」，无恶意场景下不会静默失败；
> 引擎选择/模板校验失败只会拒绝单次调用，不会崩服务（全部 try/except 容错）。

## D. 上线后观测项（运行观测台数据源）

- **指标**：route_total / rejected_total / blocked_total / engine_selected_total / stop_reached_total / output_scrubbed_total（`/skills/metrics`）。
- **审计**：最近 200 条有界轨迹（route/policy/engine/stop/output 事件，含 ts 与明细）。
- **目录**：技能启用/禁用/版本/哈希/告警（`/skills/catalog`）。
- **阈值建议**：单日 blocked_total > 0 即预警（模型连续两次越权 = 契约或系统提示需要调整）。

---

## 附：发布流程（建议）

1. 改 SKILL.md / 代码 → 本地跑 `pytest` 全绿 + 前端 tsc 0 错误；
2. `git` 提交（**人工确认，不自动提交**）→ git-sync 推 Gitea；
3. 重启后端 28000 → 验证 catalog/metrics/simulate-route；
4. 浏览器冒烟五卡 + 真实对话 1 条（户变关系）；
5. 观察 metrics 2-4 小时，确认无异常 blocked/rejected 后宣布上线。
