"""skill_policy.py - 受控执行契约硬校验中间件（受控 Skill 问答平台 v2，设计 §6）

SkillPolicyMiddleware 是"牢笼"：模型只能在契约允许的边界内做判断。
在每次工具调用前/后硬校验（设计 §6.1 的 10 项）：
  1. 工具是否在 QueryContract.allowed_tools；
  2. 是否调用了禁用工具（task/write_file/edit_file/execute/grep/glob）；
  3. 是否与已确定的唯一数据引擎一致（引擎锁定后其他查询工具立即失效）；
  4. SQL 是否来自已批准模板（template_guard，SELECT-only/表集合⊆模板/无UNION）；
  5. 是否已命中 stop_when 却继续检索（拿到结果后的终端步骤禁止再查）；
  6. 数据工具是否未经 batch_entity_source_mode 确认引擎（引擎优先）。

违反策略：第一次拒绝该调用并返回"允许的下一步"；第二次终止本轮（不再放行）。
永远不回退到不受控自由问答。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage

from app.services.query_contract import DATA_TOOLS, ENGINE_TO_TOOLS, QueryContract
from app.services.skill_catalog import get_catalog
from app.services.template_guard import validate_against_template, load_template, template_id_components

logger = logging.getLogger(__name__)

# 事件名（SSE 消费层据此推送前端"系统阻止了不合规操作"）
EVENT_POLICY_REJECTED = "policy.rejected"
EVENT_ENGINE_SELECTED = "engine.selected"
EVENT_STOP_REACHED = "stop.reached"
EVENT_TEMPLATE_BOUND = "template.bound"
EVENT_POLICY_DEGRADED = "policy.degraded"   # 批1：error_class 触发的受控降级

REJECT_MARKER = "SkillPolicy·拒绝"
BLOCK_MARKER = "SkillPolicy·已阻断"
MAX_VIOLATIONS = 2

# 带自由 sql 参数的执行工具（需模板校验）
_SQL_TOOLS = frozenset({"execute_sql", "execute_doris_sql", "execute_api_sql"})

# 批1：受控降级只放行这两个只读定位工具（重定位真实表名）
_DEGRADATION_TOOLS = frozenset({"search_entities", "list_tables"})
# 触发降级的 error_class（表/catalog 不存在/语法类 -> 允许一次重定位）
_DEGRADATION_TRIGGERS = frozenset({"TABLE_MISSING", "SYNTAX"})
# G2（融合设计 §4.3）：可纠错 error_class（计数闸门计入）；上限 2 次，超限直接终止出失败卡
# S2：聚合退化（AGGREGATE_DEGRADED）类上限放宽到 3（该错误非死循环，是模型改写聚合的方差，
# 多一次纠错机会显著收敛；其余错误类维持 2）。超限仍终止出失败卡（P0 死循环教训不变）。
_CORRECTION_LIMIT = 2
_AGGREGATE_CORRECTION_LIMIT = 3
_CORRECTABLE_CLASSES = frozenset({"TABLE_MISSING", "CATALOG_MISSING", "SYNTAX", "TIMEOUT", "AGGREGATE_DEGRADED"})
# S5（HITL v2）：表/catalog 不存在 -> 由「自动降级一次」升级为「interrupt 请求人审」；
# 仅这两类（唯一许可降级）走人审；SYNTAX 仍走自动纠错（无定位语义）。
_HITL_TRIGGERS = frozenset({"TABLE_MISSING", "CATALOG_MISSING"})
# 人审等待超时（秒）：超时视为拒绝（不授予定位许可，继续自动纠错/失败卡）
_HITL_TIMEOUT = float(os.getenv("TUPU_HITL_TIMEOUT", "180"))
# S5 待审中断注册表：interrupt_id -> asyncio.Future（await 值 {approve: bool}）
# 由 SkillPolicy 在 agent 循环内注册并 await，恢复端点按 interrupt_id 解析（跨 HTTP 请求共享）。
_HITL_INTERRUPTS: Dict[str, asyncio.Future] = {}
# G2：error_class -> 结构化纠错指引（ToolMessage 附加 correction 字段，模型据此自纠）
_CORRECTION_GUIDES = {
    "TABLE_MISSING": "表 {t} 不存在。调用 search_entities 重新定位实体，或 list_tables 查真实表名后修正重试。",
    "CATALOG_MISSING": "表/catalog 不存在。调用 search_entities 重新定位实体，或 list_tables 查真实表名后修正重试。",
    "SYNTAX": "SQL 报错（语法/列名错误）。调用 validate_attributes 校验列名后修正重试。",
    "TIMEOUT": "查询超时。移除 ORDER BY / 增加 LIMIT / 确认可否命中预聚合加速表。",
    # S1（L2）：聚合退化（结果层硬校验）——聚合分布类问题返回了明细全表
    "AGGREGATE_DEGRADED": "聚合分布类问题必须返回 GROUP BY 维度列 + COUNT/SUM 的聚合视图，当前返回了明细全表（SQL 无 GROUP BY/DISTINCT）。"
                          "请勿重复执行同样的明细 SQL；必须立即改为聚合查询：SELECT 维度列, COUNT(*) AS cnt FROM 同一表 GROUP BY 维度列（可 ORDER BY cnt DESC）。"
                          "维度列请用系统给出的维度列提示；不确定时先 sample_column_values 确认真实枚举值。",
}
_CORRECTION_GUIDE_EMPTY = "结果为空。调用 sample_column_values 检查过滤值是否真实存在，复核时间范围与口径。"


class SkillPolicyMiddleware(AgentMiddleware[Any, Any, Any]):
    """受控执行契约硬校验中间件。

    Args:
        catalog: SkillCatalog（可注入，默认单例）。
        dispatcher: 事件派发函数；默认 adispatch_custom_event。
        max_violations: 单轮最大违规次数，超过后阻断本轮。
    """

    def __init__(self, catalog=None, dispatcher: Optional[Callable[..., Awaitable[None]]] = None,
                 max_violations: int = MAX_VIOLATIONS,
                 allow_missing_contract: bool = False) -> None:
        self._catalog = catalog or get_catalog()
        self._max_violations = max_violations
        self._dispatcher = dispatcher
        # P0-1 fail-closed：默认契约缺失即拒绝全部工具；仅显式标识的兼容/测试模式放行
        self._allow_missing_contract = allow_missing_contract

    # ------------------------------------------------------------------
    # 工具调用包装
    # ------------------------------------------------------------------
    async def awrap_tool_call(self, request, handler):
        contract = self._get_contract(request)
        tool_name = request.tool_call.get("name", "")
        tc_id = request.tool_call.get("id")
        # P0-1 fail-closed：受控路径契约缺失 -> 拒绝全部工具（只有显式兼容/测试模式放行）
        if contract is None:
            if self._allow_missing_contract:
                return await handler(request)
            return await self._reject_no_contract(request, tool_name, tc_id)

        # ---- 前置校验（不调 handler 即拒绝）----
        # P2（三轮评审）：_precheck 现为 async —— SQL 模板命中时在 handler 前 await 派发
        # template.bound/drift，保证确定性顺序 template.bound → tool.started → tool.completed，
        # 且不依赖后台任务（取消/竞态不丢事件）。
        violation = await self._precheck(contract, tool_name, request)
        if violation is not None:
            return await self._do_reject(request, contract, tool_name, tc_id, violation)

        # ---- 通过：调 handler，再后置处理结果 ----
        result = await handler(request)
        try:
            self._postcheck(contract, tool_name, result, request)
            # S5（HITL v2）：表/catalog 不存在 -> 由「自动降级一次」升级为「interrupt 请求人审」
            # await 在 agent 循环内进行（yield 给事件循环，恢复端点可跨请求解析），不阻塞其他会话。
            await self._check_hitl_interrupt(contract, tool_name, result, request)
        except Exception as e:
            logger.warning(f"[SkillPolicy] postcheck 异常: {e}")
        return result
    async def _reject_no_contract(self, request, tool_name: str, tc_id) -> ToolMessage:
        """P0-1：受控契约缺失时拒绝调用（fail-closed），不执行任何工具。"""
        msg = (f"SkillPolicy·已阻断[受控契约缺失] 工具 {tool_name} 因无受控契约被拒绝（fail-closed）。"
               f"当前请求未建立路由契约，禁止执行任何业务工具。")
        try:
            await self._emit(request, EVENT_POLICY_REJECTED, {
                "tool_call_id": tc_id, "tool_name": tool_name,
                "attempt": 0, "reason": "受控契约缺失（fail-closed）", "blocked": True,
            })
        except Exception as e:
            logger.error(f"[SkillPolicy] dispatch no-contract rejected failed: {e}")
        try:
            from app.services import skill_governance as _gov
            _gov.get_governance().record_policy(
                _gov.EVENT_POLICY_BLOCKED, "__no_contract__", "__none__",
                f"tool={tool_name}: 受控契约缺失（fail-closed）")
        except Exception:
            pass
        return ToolMessage(content=msg, tool_call_id=tc_id)

    # ------------------------------------------------------------------
    # 前置校验
    # ------------------------------------------------------------------
    async def _precheck(self, contract: QueryContract, tool_name: str, request) -> Optional[str]:
        # 2) 禁用工具（绝对禁止 + 契约禁止）
        if tool_name in contract.forbidden_tools:
            return f"调用禁用工具 {tool_name}（契约禁止: {sorted(contract.forbidden_tools)}）"
        # 2a) P1-2 多引擎复合终止：两源取齐后禁止继续检索任何数据工具（先于 allowed 检查，
        #     因为 set_stop_reached 已把全部 DATA_TOOLS 移出 allowed_tools）
        if contract.is_data_tool(tool_name) and contract.multi_engine and contract.stop_reached:
            return "已命中多引擎复合终止条件（预算、成本两源均取到结果），禁止重复/继续检索"
        # 批1：受控降级——数据工具返回 TABLE_MISSING/SYNTAX 后，允许一次只读定位工具
        # （search_entities/list_tables）重定位真实表名（结构化 error_class 判据，替代字符串匹配）。
        if (tool_name in _DEGRADATION_TOOLS
                and contract._runtime.get("degradation_used")
                and not contract._runtime.get("degradation_consumed")):
            contract._runtime["degradation_consumed"] = True
            return None
        # 1) 不在允许集
        if not contract.allows(tool_name):
            allowed = sorted(set(contract.allowed_tools) - set(contract.forbidden_tools))
            return f"工具 {tool_name} 不在本步骤允许范围（允许: {allowed}）"
        # 3) 引擎一致性：数据工具必须匹配已确认引擎（单引擎锁定 / 多引擎逐源确认）
        if contract.is_data_tool(tool_name):
            if contract.multi_engine:
                confirmed = contract.confirmed_engines()
                # P1-2 复合终止：多引擎取齐后禁止继续检索任何源
                if contract.stop_reached:
                    return "已命中多引擎复合终止条件（预算、成本两源均取到结果），禁止重复/继续检索"
                if confirmed:
                    allowed = set()
                    for e in confirmed:
                        allowed |= set(ENGINE_TO_TOOLS.get(e, []))
                    if tool_name not in allowed:
                        return (f"数据源模式已确认（{sorted(confirmed)}），只允许 {sorted(allowed)}，"
                                f"禁止用 {tool_name} 切换/混用引擎")
                else:
                    return "请先调用 batch_entity_source_mode 确认预算/成本的数据源模式，再执行数据查询"
            else:
                # 6) 引擎优先：终端步骤内，数据工具前必须先经源模式工具确认引擎
                if contract.engine_locked and contract.selected_engine:
                    engine_tools = set(ENGINE_TO_TOOLS.get(contract.selected_engine, []))
                    if tool_name not in engine_tools:
                        return (f"数据引擎已锁定为 {contract.selected_engine}（{contract.engine_reason}），"
                                f"只能使用 {sorted(engine_tools)}，禁止用 {tool_name} 切换引擎重查")
                if not contract.engine_locked and not contract.engine_reason and contract.route_type == "scenario":
                    return "请先调用 batch_entity_source_mode 确认 SQL 涉及表的数据源模式，再执行数据查询"
        # 5) stop_when：终端步骤已拿到结果 -> 禁止继续检索
        if contract.is_data_tool(tool_name) and contract.result_obtained and contract._runtime.get("terminal"):
            return "已命中终止条件（已获得查询结果），禁止重复/继续检索"
        # 4) SQL 模板校验
        if tool_name in _SQL_TOOLS:
            sql = (request.tool_call.get("args") or {}).get("sql") or ""
            if sql:
                chk = await self._check_sql_against_templates(contract, sql, request=request)
                if not chk.ok:
                    return f"SQL 未通过模板校验: {chk.reason}"
        return None

    async def _check_sql_against_templates(self, contract: QueryContract, sql: str, request=None):
        """候选 SQL 必须来自本步骤任一已批准模板（表集合 ⊆ 模板，SELECT-only，无 UNION）。

        P0-2：按技能声明的 template_mode 分级 —— scenario_strict 结构指纹不一致即拒绝；
        extensible/generic 允许同表结构变化但记漂移审计；未渲染参数任何模式都拒绝。
        request：评审 P1-2（二轮/三轮）传入，await 派发 template.bound / template.drift 到 SSE。
        """
        errors = []
        templates = self._resolve_step_templates(contract)
        if not templates:
            # 契约未声明模板 -> 不阻断（generic 模式），但记录
            from app.services.template_guard import TemplateCheck
            return TemplateCheck(ok=True, reason="契约未声明 SQL 模板，跳过模板校验（generic 模式）")
        # 技能级模板校验模式（SKILL.md x_tupu.template_mode；缺省 extensible）
        mode = "scenario_extensible"
        try:
            skill = self._catalog.load_skill(contract.skill_id)
            if skill is not None and getattr(skill, "template_mode", ""):
                mode = skill.template_mode
        except Exception:
            pass
        for tpl_id, tpl_sql in templates:
            chk = validate_against_template(sql, tpl_sql, tpl_id, mode=mode)
            if chk.ok:
                await self._record_template_bind(contract, tpl_id, chk, request=request)
                return chk
            errors.append(f"{tpl_id}: {chk.reason}")
        from app.services.template_guard import TemplateCheck
        return TemplateCheck(ok=False, reason="；".join(errors[:3]) or "无可用模板")

    async def _record_template_bind(self, contract: QueryContract, tpl_id: str, chk, *, request=None) -> None:
        """批4 指纹审计：模板绑定（结构一致）或结构漂移（同表但骨架不同）记入治理轨迹。

        P1-2（二轮/三轮）：除治理审计外，**await 派发** template.bound / template.drift
        到 SSE。三轮起不再用 create_task 后台派发（顺序/必达性不稳、取消丢事件），
        改由 _precheck 在 handler 前 await，保证 template.bound → tool.started → tool.completed。
        """
        event_name = EVENT_TEMPLATE_BOUND if chk.structure_match else "template.drift"
        detail = (f"tpl={tpl_id} fp={chk.template_fingerprint}"
                  if chk.structure_match
                  else f"tpl={tpl_id}: 结构漂移（同表骨架不一致）fp={chk.candidate_fingerprint}")
        try:
            from app.services.skill_governance import get_governance
            get_governance().record_policy(event_name, contract.skill_id, contract.workflow_step, detail)
        except Exception:
            pass
        # P1-2：SSE 实时事件 —— await 派发（与 _do_reject 同机制，运行上下文内可靠投递）
        if request is not None:
            try:
                await self._emit(request, event_name, {
                    "detail": detail,
                    "structure_match": bool(chk.structure_match),
                    "template_id": tpl_id,
                })
            except Exception as e:
                logger.warning(f"[SkillPolicy] template 事件派发失败: {e}")

    def _resolve_step_templates(self, contract: QueryContract):
        """解析契约 template_ids -> [(template_id, 模板SQL)]（相对 SKILL.md 路径）。

        模板内 ⟦实体中文名⟧ 引用在运行时解析为物理表名（与 read_file 注入同一解析器），
        保证"候选 SQL(物理表名) 表集合 ⊆ 模板(物理表名) 表集合"可比对。
        """
        skill = self._catalog.load_skill(contract.skill_id)
        if skill is None:
            return []
        from app.services.tupu_deepagent import _resolve_entity_refs
        from app.services.template_guard import resolve_entity_aliases
        out = []
        for tpl_id in contract.template_ids:
            _, rel = template_id_components(tpl_id)
            if not rel:
                continue
            p = skill.path.parent / rel
            try:
                raw = load_template(p)
                # 先按 SKILL.md x_tupu.entity_aliases 替换 ⟦业务中文名⟧ -> 物理表名，
                # 再精确 entity_name 解析兜底（覆盖 aliases 未声明但 DB 精确命中的引用）。
                resolved = resolve_entity_aliases(raw, skill.entity_aliases)
                resolved = _resolve_entity_refs(resolved)
                out.append((tpl_id, resolved))
            except Exception as e:
                logger.warning(f"[SkillPolicy] 模板加载失败 {p}: {e}")
        return out

    # ------------------------------------------------------------------
    # 后置处理（引擎锁定 / 结果标记 / 事件派发）
    # ------------------------------------------------------------------
    def _postcheck(self, contract: QueryContract, tool_name: str, result, request) -> None:
        out_str = _result_text(result)
        # S1（L2）：执行类工具从 tool_call 参数取 SQL 兜底（结果文本不可解析时仍能判定聚合退化）
        _sql_hint = ""
        try:
            _sql_hint = str((request.tool_call.get("args") or {}).get("sql", ""))
        except Exception:
            _sql_hint = ""
        # G2：error_class/空结果 -> ToolMessage 附加结构化纠错指引（模型据此自纠）
        self._inject_correction_guidance(contract, tool_name, result, out_str, _sql_hint)
        # 批1：error_class 结构化判据 -> 表/catalog 不存在允许一次受控降级（重定位）
        self._check_controlled_degradation(contract, tool_name, out_str, request, _sql_hint)
        # 数据源模式确认（batch_entity_source_mode / get_entity_source_mode）-> 锁定/确认引擎
        if tool_name in ("batch_entity_source_mode", "get_entity_source_mode"):
            self._confirm_engine_from_result(contract, tool_name, out_str, request)
        # 数据工具返回 row_count >= 0 -> 标记结果（单引擎 result_obtained / 多引擎按源标记）
        if contract.is_data_tool(tool_name) and _has_row_count(out_str):
            if contract.multi_engine:
                engine = contract.engine_for_tool(tool_name)
                if engine:
                    contract.mark_engine_result(engine)
                # 评审 P1-1（二轮）：按实体/数据角色标记完成（工具参数 entity_code），
                # 终止看 completed_entities 覆盖 required_entities（同引擎多实体不提前误判）
                try:
                    ec = (request.tool_call.get("args") or {}).get("entity_code")
                except Exception:
                    ec = None
                contract.mark_entity_result(str(ec) if ec else None)
                # P1-2 复合终止：两源均取到 -> stop.reached + 移除全部数据工具
                if contract.multi_engine_done():
                    contract.set_stop_reached()
                    try:
                        asyncio.get_running_loop().create_task(self._emit(request, EVENT_STOP_REACHED, {
                            "tool_call_id": request.tool_call.get("id"),
                            "tool_name": tool_name,
                            "multi_engine": True,
                            "completed_entities": sorted(contract._runtime.get("completed_entities") or []),
                            "completed_engines": sorted(contract._runtime.get("result_by_engine", {})),
                            "contract": contract.to_dict(),
                        }))
                    except Exception as e:
                        logger.warning(f"[SkillPolicy] 多引擎终止事件派发失败: {e}")
                    try:
                        from app.services.skill_governance import EVENT_STOP_REACHED as G_EVENT
                        from app.services.skill_governance import get_governance
                        get_governance().record_policy(G_EVENT, contract.skill_id, contract.workflow_step,
                                                       f"multi-engine done: {sorted(contract.confirmed_engines())}")
                    except Exception:
                        pass
            else:
                contract.mark_result()
                if contract._runtime.get("terminal"):
                    try:
                        asyncio.get_running_loop().create_task(self._emit(request, EVENT_STOP_REACHED, {
                            "tool_call_id": request.tool_call.get("id"),
                            "tool_name": tool_name, "contract": contract.to_dict(),
                        }))
                    except Exception as e:
                        logger.warning(f"[SkillPolicy] 终止事件派发失败: {e}")
                    # 批4 治理：记录终止审计
                    try:
                        from app.services.skill_governance import EVENT_STOP_REACHED as G_EVENT
                        from app.services.skill_governance import get_governance
                        get_governance().record_policy(G_EVENT, contract.skill_id, contract.workflow_step, f"tool={tool_name}")
                    except Exception:
                        pass

    def _inject_correction_guidance(self, contract, tool_name: str, result, out_str: str,
                                    sql_hint: str = "") -> None:
        """G2：数据工具结果 dict 附加结构化 correction 指引（随 ToolMessage 透给模型）。

        仅执行类数据工具；error_class ∈ 可纠错集 -> 按模板注入；成功但 0 行 -> 空结果指引；
        S1（L2）：聚合意图下成功但未聚合 -> 注入聚合退化改写指引。
        dict 结果写 correction 字段；ToolMessage 结果 content 前置 [纠错指引]（S1 修复）。
        """
        if tool_name not in ("execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api"):
            return
        # 已带 correction（dict 字段 / ToolMessage 已前置指引）不重复注入
        if isinstance(result, dict) and "correction" in result:
            return
        if hasattr(result, "content") and "[纠错指引]" in str(result.content):
            return
        data = _parse_tool_json(out_str)
        ec = data.get("error_class")
        if ec in _CORRECTION_GUIDES:
            if ec == "TABLE_MISSING":
                # 尝试从 error 文本提取表名
                _tn = ""
                try:
                    import re as _re
                    _m = _re.search(r"Table '[^']*?\.?([^'.]+)'", str(data.get("error", "")))
                    if _m:
                        _tn = _m.group(1)
                except Exception:
                    pass
                _set_correction(result, _CORRECTION_GUIDES[ec].format(t=_tn or "（见错误信息）"))
            else:
                _set_correction(result, _CORRECTION_GUIDES[ec])
        elif ec is None and data.get("row_count") == 0:
            _set_correction(result, _CORRECTION_GUIDE_EMPTY)
        elif _is_aggregate_degraded(contract, data, sql_hint):
            _dim = contract.aggregate_intent.get("dimension_hint")
            if _dim:
                # 维度列提示（S2）：直接给出目标列 -> 显式要求 SELECT {dim}, COUNT(*) AS cnt ... GROUP BY {dim}
                _set_correction(result, _CORRECTION_GUIDES["AGGREGATE_DEGRADED"] +
                                f"本问题维度列确定为 {_dim}，请执行 SELECT {_dim}, COUNT(*) AS cnt FROM 同一表 GROUP BY {_dim}。")
            else:
                _set_correction(result, _CORRECTION_GUIDES["AGGREGATE_DEGRADED"])

    def _check_controlled_degradation(self, contract: QueryContract, tool_name: str,
                                      out_str: str, request, sql_hint: str = "") -> None:
        """G2 计数闸门 + 批1 受控降级。

        数据工具返回可纠错 error_class -> contract._runtime["corrections"] +1；
        超 _CORRECTION_LIMIT(2) -> set_stop_reached（移除全部数据工具 + terminal），
        出失败卡（P0 死循环教训制度化）；未超限且属降级触发类 -> 授予一次
        search_entities/list_tables 定位许可（_precheck 消费）。治理 + SSE 双落。
        """
        if tool_name not in ("execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api"):
            return
        data = _parse_tool_json(out_str)
        ec = data.get("error_class")
        # S1（L2）：聚合退化（成功但未聚合）-> 计入纠错闭环（上限 2 次、超限失败卡）
        if ec is None and _is_aggregate_degraded(contract, data, sql_hint):
            ec = "AGGREGATE_DEGRADED"
        if ec not in _CORRECTABLE_CLASSES:
            return
        # 计数闸门
        corrections = int(contract._runtime.get("corrections", 0)) + 1
        contract._runtime["corrections"] = corrections
        # S2：聚合退化类上限放宽到 3（改写聚合方差多一次机会），其余类维持 2
        _limit = _AGGREGATE_CORRECTION_LIMIT if ec == "AGGREGATE_DEGRADED" else _CORRECTION_LIMIT
        _stopped = False
        if corrections > _limit:
            _stopped = True
            contract.set_stop_reached()  # 移除数据工具 + terminal -> 后续数据工具调用被拒，出失败卡
            try:
                from app.services.skill_governance import get_governance
                get_governance().record_policy(
                    "correction.limit", contract.skill_id, contract.workflow_step,
                    f"corrections={corrections} > {_limit} -> 终止（失败卡）")
            except Exception:
                pass
            try:
                asyncio.get_running_loop().create_task(self._emit(request, "correction.attempt", {
                    "tool_call_id": request.tool_call.get("id"),
                    "tool_name": tool_name, "error_class": ec,
                    "attempt": corrections, "limit": _limit, "stopped": True,
                    "reason": f"纠错超限（{corrections}>{_limit}），已终止并出失败卡",
                    "contract": contract.to_dict(),
                }))
            except Exception as e:
                logger.warning(f"[SkillPolicy] correction.limit 事件派发失败: {e}")
            return
        # 批1：表/catalog/语法类 -> 授予一次受控降级（重定位）
        # S5（HITL v2）：契约开启人审且属表/catalog 不存在类 -> 不自动降级，
        # 由 _check_hitl_interrupt await 人审决定是否授予（批准才置 degradation_used）。
        if ec in _DEGRADATION_TRIGGERS and not contract._runtime.get("degradation_used") \
                and not (getattr(contract, "hitl_enabled", False) and ec in _HITL_TRIGGERS):
            contract._runtime["degradation_used"] = True
            contract._runtime["degradation_reason"] = f"tool={tool_name} error_class={ec}"
            # 治理审计
            try:
                from app.services.skill_governance import get_governance
                get_governance().record_policy(
                    "policy.degraded", contract.skill_id, contract.workflow_step,
                    f"error_class={ec} tool={tool_name} -> 允许一次 search_entities/list_tables")
            except Exception:
                pass
        # 每次纠错记 correction.attempt 事件（治理 + SSE 双落）
        try:
            from app.services.skill_governance import get_governance
            get_governance().record_policy(
                "correction.attempt", contract.skill_id, contract.workflow_step,
                f"error_class={ec} tool={tool_name} attempt={corrections}")
        except Exception:
            pass
        try:
            asyncio.get_running_loop().create_task(self._emit(request, "correction.attempt", {
                "tool_call_id": request.tool_call.get("id"),
                "tool_name": tool_name, "error_class": ec,
                "attempt": corrections, "limit": _limit, "stopped": False,
                "reason": f"纠错第 {corrections} 次（上限 {_limit}）",
                "contract": contract.to_dict(),
            }))
        except Exception as e:
            logger.warning(f"[SkillPolicy] correction.attempt 事件派发失败: {e}")

    async def _check_hitl_interrupt(self, contract: QueryContract, tool_name: str,
                                    result, request) -> None:
        """S5（HITL v2）：表/catalog 不存在 -> interrupt 请求人审（升级「自动降级一次」）。

        契约 `hitl_enabled=True`（free_plan generic 路径开启）且首个 TABLE_MISSING/CATALOG_MISSING：
          1. 派发 `policy.interrupt` 事件 {interrupt_id, reason, proposal}（SSE 给前端横条）；
          2. 注册 asyncio.Future 并 `await`（yield 给事件循环，恢复端点可跨 HTTP 请求解析）；
          3. 批准 -> 授予一次 search_entities/list_tables 定位许可（degradation_used=True）；
             拒绝/超时 -> 不授予（agent 按纠错指引继续，可能重试后出失败卡）。

        会话锁注：本方法在 agent 循环内 await，恢复端点**不得**获取会话锁（锁被本流持有，
        再获取即死锁——S5 验收③「会话锁无死锁」的落点）。
        """
        try:
            if not getattr(contract, "hitl_enabled", False):
                return
            if contract._runtime.get("degradation_used") or contract._runtime.get("hitl_pending"):
                return  # 已批准过定位许可 / 已有待审中断 -> 不重复打断
            if tool_name not in _SQL_TOOLS and tool_name != "execute_entity_api":
                return
            data = _parse_tool_json(_result_text(result))
            ec = data.get("error_class")
            if ec not in _HITL_TRIGGERS:
                return
            _fut = asyncio.get_running_loop().create_future()
            _interrupt_id = str(uuid.uuid4())
            contract._runtime["hitl_pending"] = True
            _HITL_INTERRUPTS[_interrupt_id] = _fut
            _reason = f"工具 {tool_name} 返回 {ec}：查询的表/catalog 不存在。"
            _proposal = "允许调用 search_entities / list_tables 重定位真实表名后重试（仅一次）。"
            try:
                await self._emit(request, "policy.interrupt", {
                    "interrupt_id": _interrupt_id,
                    "reason": _reason,
                    "proposal": _proposal,
                    "tool_name": tool_name,
                    "error_class": ec,
                })
            except Exception as _e:
                logger.warning(f"[SkillPolicy] policy.interrupt 事件派发失败: {_e}")
            try:
                _decision = await asyncio.wait_for(_fut, timeout=_HITL_TIMEOUT)
            except asyncio.TimeoutError:
                _decision = None
            finally:
                _HITL_INTERRUPTS.pop(_interrupt_id, None)
                contract._runtime["hitl_pending"] = False
            _approve = bool(_decision.get("approve")) if isinstance(_decision, dict) else False
            if _approve:
                contract._runtime["degradation_used"] = True
                contract._runtime["degradation_reason"] = f"HITL 批准: tool={tool_name} error_class={ec}"
                logger.info(f"[SkillPolicy] HITL 批准 {_interrupt_id}: {tool_name} {ec} -> 授予定位许可")
            else:
                logger.info(f"[SkillPolicy] HITL 拒绝/超时 {_interrupt_id}: {tool_name} {ec} -> 不授予定位许可")
            try:
                from app.services.skill_governance import get_governance
                get_governance().record_policy(
                    "policy.interrupt", contract.skill_id, contract.workflow_step,
                    f"error_class={ec} tool={tool_name} interrupt={_interrupt_id} approved={_approve}")
            except Exception:
                pass
        except asyncio.CancelledError:
            raise
        except Exception as _e:
            logger.warning(f"[SkillPolicy] HITL interrupt 流程异常（不阻塞主链路）: {_e}")

    def _confirm_engine_from_result(self, contract: QueryContract, tool_name: str,
                                    out_str: str, request) -> None:
        """源模式工具真实返回 -> 单引擎锁定 / 多引擎逐源确认（引擎不由模型拍板）。

        评审 P1-1：逐实体确认**每次真实返回新引擎都并入集合**（不再要求 confirmed 为空），
        重复值由 confirm_engines 集合去重；同时记录 实体->引擎 映射。
        """
        try:
            import json
            data = json.loads(out_str) if out_str else {}
        except Exception:
            data = {}
        if not isinstance(data, dict):
            return
        if contract.multi_engine:
            from app.services.query_engine_router import SOURCE_MODE_TO_ENGINE, resolve_engines_multi
            engines = resolve_engines_multi(data)
            # 实体 -> 引擎 映射（batch items 逐实体）
            eem = {}
            for it in (data.get("items") or []):
                ec = str(it.get("entity_code") or "")
                sm = str(it.get("source_mode") or "")
                en = SOURCE_MODE_TO_ENGINE.get(sm)
                if ec and en:
                    eem[ec] = en
            if not engines:
                # 单实体 get_entity_source_mode：source_mode -> engine + 实体映射
                sm = data.get("source_mode") or ""
                e = SOURCE_MODE_TO_ENGINE.get(sm)
                engines = [e] if e else None
                ec = str(data.get("entity_code") or "")
                if e and ec:
                    eem[ec] = e
            if engines:
                contract.add_entity_engines(eem)
                contract.confirm_engines(engines, f"{tool_name} 返回 source_mode: {sorted(engines)}")
                # 评审 P1-1（二轮）：确认阶段记实体（required_entities 判定终止用）
                entity_codes = list(eem.keys())
                if eem:
                    contract.confirm_entities(entity_codes)
                try:
                    asyncio.get_running_loop().create_task(self._emit(request, EVENT_ENGINE_SELECTED, {
                        "tool_call_id": request.tool_call.get("id"),
                        "selected_engine": ",".join(contract.confirmed_engines()),
                        "multi_engine": True, "reason": contract.engine_reason,
                        "entity_engine_map": dict(contract.entity_engine_map),
                        "contract": contract.to_dict(),
                    }))
                except Exception as e:
                    logger.warning(f"[SkillPolicy] 多引擎事件派发失败: {e}")
                try:
                    from app.services.skill_governance import EVENT_ENGINE_SELECTED as G_EVENT
                    from app.services.skill_governance import get_governance
                    get_governance().record_policy(G_EVENT, contract.skill_id, contract.workflow_step,
                                                   f"multi: {sorted(engines)}")
                except Exception:
                    pass
            return
        # 单引擎：锁定唯一引擎
        engine, reason = self._engine_from_source_mode(out_str)
        if engine and not contract.engine_locked:
            contract.lock_engine(engine, reason or f"{tool_name} 推荐: {engine}")
            try:
                asyncio.get_running_loop().create_task(self._emit(request, EVENT_ENGINE_SELECTED, {
                    "tool_call_id": request.tool_call.get("id"),
                    "selected_engine": engine, "reason": reason,
                    "contract": contract.to_dict(),
                }))
            except Exception as e:
                logger.warning(f"[SkillPolicy] 引擎事件派发失败: {e}")
            # 批4 治理：记录引擎选择审计
            try:
                from app.services.skill_governance import EVENT_ENGINE_SELECTED as G_EVENT
                from app.services.skill_governance import get_governance
                get_governance().record_policy(G_EVENT, contract.skill_id, contract.workflow_step, reason or engine)
            except Exception:
                pass

    def _engine_from_source_mode(self, out_str: str):
        """按源模式真实返回解析唯一引擎（batch 的 recommended_tool / 单实体 source_mode）。"""
        import json
        try:
            data = json.loads(out_str) if out_str else {}
        except Exception:
            return None, None
        if not isinstance(data, dict):
            return None, None
        from app.services.query_engine_router import SOURCE_MODE_TO_ENGINE, resolve_engine
        decision = resolve_engine(data)
        if decision is not None:
            return decision.engine, decision.reason
        sm = data.get("source_mode") or ""
        e = SOURCE_MODE_TO_ENGINE.get(sm)
        if e:
            return e, f"{data.get('entity_code') or '?'} source_mode={sm}"
        return None, None

    # ------------------------------------------------------------------
    # 拒绝路径
    # ------------------------------------------------------------------
    async def _do_reject(self, request, contract, tool_name: str, tc_id, violation: str) -> ToolMessage:
        n = contract.record_violation()
        if n >= self._max_violations:  # 第2次违规即终止本轮（设计 §6.3：第一次指引，第二次终止）
            msg = (f"{BLOCK_MARKER}[违规{n}次已阻断本轮] {violation}。"
                   f"不要再重试该调用，请基于已有信息直接回答用户，或说明因受控策略无法完成。")
        else:
            msg = (f"{REJECT_MARKER}[第{n}次] {violation}。"
                   f"原工具未执行。请按受控契约调整：只调用允许工具，使用已批准 SQL 模板，"
                   f"满足终止条件后立即结束并基于已有结果回答。")
        try:
            await self._emit(request, EVENT_POLICY_REJECTED, {
                "tool_call_id": tc_id, "tool_name": tool_name,
                "attempt": n, "reason": violation,
                "allowed_tools": sorted(set(contract.allowed_tools) - set(contract.forbidden_tools)),
                "blocked": n > self._max_violations,
            })
        except Exception as e:
            logger.error(f"[SkillPolicy] dispatch rejected failed: {e}")
        # 批4 治理：记录拒绝/阻断审计（第2次起为阻断）
        try:
            from app.services import skill_governance as _gov
            ev = _gov.EVENT_POLICY_BLOCKED if n >= self._max_violations else _gov.EVENT_POLICY_REJECTED
            _gov.get_governance().record_policy(
                ev, contract.skill_id, contract.workflow_step,
                f"tool={tool_name}: {violation}", attempt=n,
            )
        except Exception:
            pass
        return ToolMessage(content=msg, tool_call_id=tc_id)

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _get_contract(request) -> Optional[QueryContract]:
        runtime = getattr(request, "runtime", None)
        ctx = getattr(runtime, "context", None) or {}
        return ctx.get("contract") if isinstance(ctx, dict) else None

    async def _emit(self, request, event_name: str, payload: dict) -> None:
        if self._dispatcher is not None:
            await self._dispatcher(event_name, payload, getattr(request.runtime, "config", None))
            return
        from langchain_core.callbacks import adispatch_custom_event
        await adispatch_custom_event(event_name, payload, config=getattr(request.runtime, "config", None))


def _result_text(result) -> str:
    """把 handler 返回结果转字符串（兼容 str / ToolMessage / dict）。

    dict -> json.dumps；ToolMessage.content 为 langchain 块列表时提取首个 text 块。
    S1（L2）修复：原 str(dict)/str(块列表) 为 Python repr，json.loads 失败，
    导致 G2 error_class 计数与聚合退化判定同时失效。
    """
    if result is None:
        return ""
    if isinstance(result, dict):
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception:
            return str(result)
    if hasattr(result, "content"):
        _c = result.content
        if isinstance(_c, list):
            for _b in _c:
                if isinstance(_b, dict) and _b.get("type") == "text" and isinstance(_b.get("text"), str):
                    return _b["text"]
            return str(_c)
        return str(_c or "")
    return str(result)


def _parse_tool_json(out_str: str) -> dict:
    """解析数据工具结果文本为 dict（S1 L2 修复）。

    MCP 工具输出为 `{"type":"text","text":"<内层JSON>"}` 双层包装：先 json.loads 外层，
    若为 text 包装则再解析内层（与 DataSummary 解嵌套逻辑一致），返回内层结果 dict。
    """
    if not out_str:
        return {}
    try:
        data = json.loads(out_str)
    except Exception:
        return {}
    if isinstance(data, dict) and data.get("type") == "text" and isinstance(data.get("text"), str):
        try:
            inner = json.loads(data["text"])
            if isinstance(inner, dict):
                return inner
        except Exception:
            pass
    return data if isinstance(data, dict) else {}


def _is_aggregate_degraded(contract, data, sql_hint: str = "") -> bool:
    """S1（L2）：聚合意图 + 成功数据结果未做聚合 -> True。

    判定（结果文本不可解析时以 tool 参数 sql 兜底）：aggregate_intent 在契约
    && 结果成功（无 error_class/error——被拒/报错结果不算聚合退化）
    && 实际执行 SQL 无 GROUP BY/DISTINCT。
    聚合分布类问题的正确形态必须是 GROUP BY 维度列 + COUNT/SUM；任何无聚合的
    明细/标量查询都视为聚合退化（明细全表或纯 COUNT 总数都不构成分布视图）。
    """
    if not getattr(contract, "aggregate_intent", None):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("error_class") or data.get("error"):
        return False  # 失败/被拒结果不算聚合退化
    # 仅当确认是数据结果（有 row_count/columns）才判定——不可解析/拒绝文本不误判
    has_result = data.get("row_count") is not None or data.get("columns") is not None
    if not has_result:
        return False
    sql = str(data.get("sql") or sql_hint or "")
    if not sql:
        return False
    import re as _re
    if _re.search(r"\bGROUP\s*BY\b|\bDISTINCT\b", sql, _re.IGNORECASE):
        return False
    return True


def _set_correction(result, text: str) -> None:
    """把结构化纠错指引写到结果上（dict -> correction 字段；ToolMessage -> content 前置 [纠错指引]）。

    S1（L2）修复：生产环境数据工具结果为 ToolMessage（content 为 langchain 块列表），
    原 `result["correction"]` 仅对 dict 生效（单测外从未抵达模型）；此处与 DataSummary
    同款 object.__setattr__ 前置指引，让模型实际看到纠错内容。
    """
    if not text:
        return
    if isinstance(result, dict):
        result["correction"] = text
        return
    if hasattr(result, "content"):
        _prefix = f"[纠错指引] {text}"
        _c = result.content
        if isinstance(_c, list):
            _blocks = list(_c)
            for _i, _b in enumerate(_blocks):
                if isinstance(_b, dict) and _b.get("type") == "text" and isinstance(_b.get("text"), str):
                    _nb = dict(_b)
                    _nb["text"] = _prefix + "\n\n" + _b["text"]
                    _blocks[_i] = _nb
                    break
            else:
                _blocks.insert(0, {"type": "text", "text": _prefix})
            try:
                object.__setattr__(result, "content", _blocks)
            except Exception:
                pass
        else:
            try:
                object.__setattr__(result, "content", _prefix + "\n\n" + str(_c or ""))
            except Exception:
                pass


def _has_row_count(out_str: str) -> bool:
    import re as _re
    # row_count 出现在结果里即视为有数据（含 0 行：拿到查询结果即终止）
    return bool(_re.search(r"['\"]row_count['\"]\s*:\s*\d+", out_str))


# ---------------------------------------------------------------------------
# S5（HITL v2）人审恢复 —— 模块级函数（必须置于类之后，否则会被 Python 视为类内嵌套）
# ---------------------------------------------------------------------------
def resolve_hitl_interrupt(interrupt_id: str, approve: bool) -> bool:
    """恢复端点调用：按 interrupt_id 解析待审 Future（approve: bool）。

    返回 False 表示中断不存在/已处理（如已超时或已由其他请求恢复）。不抛异常。
    """
    _fut = _HITL_INTERRUPTS.get(interrupt_id)
    if _fut is None or _fut.done():
        return False
    _fut.set_result({"approve": bool(approve)})
    return True


def pending_hitl_interrupts_count() -> int:
    """待审中断数（观测/测试用）。"""
    return len(_HITL_INTERRUPTS)
