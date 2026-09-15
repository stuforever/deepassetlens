import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# 安全控制中心基线策略（《安全控制中心实施设计》2.1 种子数据）
# 六条：五类对外（capability/sql_safety/template/engine_lock/output）+ 审批轨（approval_track）
GUARD_POLICY_SEED = [
    {
        "guard_id": "capability",
        "title": "能力控制",
        "risk_level": "red",
        "params": {"forbidden_tools": ["task", "write_file", "edit_file", "execute", "grep", "glob"],
                   "absolute_tools": ["execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api"]},
        "description": {
            "what": "限制模型可调用的工具集合：全局硬禁危险工具（task 子代理/写文件/Shell 执行），仅放行受控数据工具与只读检索工具。",
            "lose": "关闭后模型可调用 task 子代理、写文件、执行 Shell 等高风险工具，具备逃逸能力。",
            "remain": "SQL 执行仍受 SQL 安全控制与模板控制保护，但工具面显著扩大。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "sql_safety",
        "title": "SQL 安全控制",
        "risk_level": "red",
        "params": {"limit_max": 500, "func_blacklist": ["sleep", "benchmark", "load_file", "pg_sleep", "into_outfile"]},
        "description": {
            "what": "对 SQL 型工具做 AST 级安全校验：只读语句（SELECT/WITH）、禁副作用函数、表白名单、强制 LIMIT。",
            "lose": "关闭后 DDL/DML/危险函数/超大结果集将直接放行，存在数据损坏与注入风险。",
            "remain": "模板控制仍拦截越表 SQL，但非模板路径的 SQL 将失去机械安全校验。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "template",
        "title": "模板控制",
        "risk_level": "yellow",
        "params": {"strict": True},
        "description": {
            "what": "受控场景下 SQL 必须来自已批准模板（表集合 ⊆ 模板、SELECT-only、无 UNION 绕过），结构指纹与模板一致才放行。",
            "lose": "关闭后模型可自由拼装 SQL 结构，表集合校验失效，数据语义可能跑偏。",
            "remain": "SQL 安全控制仍拦截非只读语句，但模板约束消失。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "engine_lock",
        "title": "引擎控制",
        "risk_level": "yellow",
        "params": {"lock_engine": True},
        "description": {
            "what": "数据工具必须匹配已确认的数据引擎（单引擎锁定 / 多引擎逐源确认），引擎由平台锁定不由模型拍板。",
            "lose": "关闭后模型可跨引擎混查，结果可能来自错误数据源且无一致性保障。",
            "remain": "数据源模式守卫仍拦截 execute_sql 对非 physical_table 的误用。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "output",
        "title": "输出控制",
        "risk_level": "yellow",
        "params": {"forbid_markdown_detail_table": True},
        "description": {
            "what": "控制最终答案输出形态：禁止与结果表同字段的 Markdown 明细表，强制结论/发现/建议分层输出。",
            "lose": "关闭后模型可输出冗余明细表，前端展示被遮挡，回答结构退化。",
            "remain": "查询结果表仍由前端权威渲染，不影响数据本身。",
        },
        "confirm_required": True,
    },
    {
        "guard_id": "approval_track",
        "title": "审批轨",
        "risk_level": "green",
        "params": {"interrupt_on": ["step2_power_aggregation", "step3_load_ratio"]},
        "description": {
            "what": "高风险步骤（功率汇集/负载倒排）执行前装配审批中断点，拦截时进入人工审批队列。",
            "lose": "关闭后高风险步骤直接自动执行，跳过人工审批环节。",
            "remain": "拦截记录仍留痕，只是不再阻塞等待审批。",
        },
        "confirm_required": False,
    },
]


def _seed_guard_policies(db: Session):
    """安全控制中心基线策略种子：仅当表为空时插入（幂等）。"""
    from ..models.base import GuardPolicy
    if db.query(GuardPolicy).first():
        return
    for p in GUARD_POLICY_SEED:
        db.add(GuardPolicy(
            guard_id=p["guard_id"], title=p["title"], enabled=True, mode="block",
            params=p.get("params"), risk_level=p["risk_level"],
            description=p.get("description"), confirm_required=p.get("confirm_required", True),
            version=1,
        ))
    db.commit()


# ---------------------------------------------------------------------------
# 能力开关中心基线（批13-Q，16 行：14 可切 + 4 灰显锁定；默认基线全开）
# ---------------------------------------------------------------------------
_CAP_DESC = lambda what, lose, remain: {"what": what, "lose": lose, "remain": remain}


def _w1_default_allowed():
    """W-1 白名单默认允许集（勾选域全勾=MCP 17 件+task）。本地实现防与 capability_config 循环导入。"""
    try:
        from ..services.query_contract import GENERIC_ALLOWED_TOOLS
        return sorted(set(GENERIC_ALLOWED_TOOLS) | {"task"})
    except Exception:
        return ["task"]


CAPABILITY_POLICY_SEED = [
    {"capability_id": "skills", "title": "技能包", "risk_level": "yellow",
     "description": _CAP_DESC("装配 SkillsMiddleware：Agent 自动发现 data/skills 下 SKILL.md 并按需读取子文件（场景剧本/参考/模板）。",
                              "关闭后场景剧本路由失去技能文件支撑，Agent 只能靠系统提示词与 MCP 工具裸跑。",
                              "受控契约/模板/引擎守卫仍生效；generic 链路不受影响。"), "confirm_required": True},
    {"capability_id": "filesystem_tools", "title": "文件系统工具", "risk_level": "yellow",
     "description": _CAP_DESC("装配 CompositeBackend：/skills/ 只读技能目录、/memory/ 只读纪律文件，提供 ls/read_file 等文件工具。",
                              "关闭后 Agent 无法读取 SKILL.md 与模板文件，技能依赖 read_file 的链路退化。",
                              "文件写操作本就被 permissions 拒绝；MCP 数据工具不受影响。"), "confirm_required": True},
    {"capability_id": "memory", "title": "常驻记忆", "risk_level": "yellow",
     "description": _CAP_DESC("装配 MemoryMiddleware：注入 /memory/AGENTS.md 常驻纪律（全局长期纪律，运营可改文件）。",
                              "关闭后全局纪律文件不再注入，跨会话纪律约束消失。",
                              "单次会话的系统提示词与契约约束不受影响。"), "confirm_required": True},
    {"capability_id": "summarization", "title": "上下文摘要", "risk_level": "yellow",
     "description": _CAP_DESC("装配保守摘要件（30k token 触发/保留10条/参数截断15条）+ compact_conversation 手动压缩工具。",
                              "关闭后长会话不再自动压缩，可能触达模型上下文上限导致报错。",
                              "compact_conversation 工具随之消失；单轮问答不受影响。"), "confirm_required": True},
    {"capability_id": "rubric", "title": "自评闸门", "risk_level": "yellow",
     "description": _CAP_DESC("装配 RubricMiddleware：generic 契约回答后按 rubric 自评一轮（只评不改）。",
                              "关闭后回答不再自评，rubric 违例不再可观测。",
                              "数据校验（validate_safe_sql/ScopeChecker）与守卫面不受影响。"), "confirm_required": True},
    {"capability_id": "patch_tool_calls", "title": "悬空调用修复", "risk_level": "green",
     "description": _CAP_DESC("框架自动装配 PatchToolCallsMiddleware：修复会话中断后的悬空 tool_calls（补 cancelled ToolMessage）。",
                              "框架恒装（无装配参数），开关作用于装配清单记录与审计；关闭仅移除清单标记。",
                              "修复逻辑本身无安全语义，恒在无风险。"), "confirm_required": False},
    {"capability_id": "message_eviction", "title": "消息淘汰", "risk_level": "green",
     "description": _CAP_DESC("框架自动的消息淘汰健壮件（超长历史裁剪，防上下文溢出）。",
                              "框架恒装（无装配参数），开关作用于装配清单记录与审计；关闭仅移除清单标记。",
                              "摘要件关闭时本件是最后一道上下文溢出防线。"), "confirm_required": False},
    {"capability_id": "response_format", "title": "结构化最终交付", "risk_level": "yellow",
     "params": {"schema": "final"},
     "description": _CAP_DESC("给 Agent 配 response_format（final 扁平 schema）：最终答案走结构化通道（F5 统一交付协议）。",
                              "关闭后回退文本答案 + data_intelligence A-E 确定性降级策略（现状行为）。",
                              "回答内容本身不受影响；A-E 降级恒在。"), "confirm_required": True},
    {"capability_id": "store", "title": "长期记忆库", "risk_level": "yellow",
     "params": {"max_prefs": 5},
     "description": _CAP_DESC("注入 InMemoryStore：支持跨会话命名空间偏好存取（批13-F store 件）。",
                              "关闭后偏好存取工具不可用，跨会话个性化退化。",
                              "checkpointer 会话记忆不受影响。"), "confirm_required": True},
    {"capability_id": "subagents", "title": "子代理（受限）", "risk_level": "red",
     "params": {"specs": [{"name": "entity_locator",
                           "description": "按业务域并行定位实体表，返回候选清单（code/name/引擎/置信度）",
                           "prompt": "只做实体定位与校验，不做 SQL 拼装，不做跨域推断，不超出给定工具。",
                           "tools": ["search_entities", "search_entities_batch", "fetch_l1_l2_tree", "validate_l2", "fetch_subgraph"]}],
                "max_concurrent": 2},
     "description": _CAP_DESC("装配 task 委派工具与声明式子代理规格（与父代理同栈共享守卫链）；工具集=全局白名单子集。",
                              "委派面扩大（并发上下文隔离的子代理），靠四护栏约束：契约 allow_subagents 复合条件/继承守卫/白名单窄化/全程审计。",
                              "关闭或护栏拒绝时回退串行定位（委派是加速器不是依赖项）；守卫面（SQL/模板/引擎）对子代理仍生效。"), "confirm_required": True},
    {"capability_id": "permissions", "title": "文件权限规则", "risk_level": "yellow",
     "description": _CAP_DESC("装配 FilesystemPermission 规则：允许读 /skills/**，拒绝其余读与全部写。",
                              "关闭后文件工具不再有 allow/deny 规则约束（backend 路由仍限制在 /skills/ /memory/ 根内）。",
                              "virtual_mode 防目录穿越仍生效；write_file 在工具排除清单本就不可用。"), "confirm_required": True},
    {"capability_id": "debug", "title": "调试模式", "risk_level": "yellow",
     "description": _CAP_DESC("create_deep_agent(debug=True)：框架图执行详细日志（开发排障用）。",
                              "关闭后框架回归常规日志级别（生产推荐）。",
                              "业务行为无差异；仅日志详细度变化。"), "confirm_required": True},
    {"capability_id": "approval_track", "title": "审批轨", "risk_level": "green",
     "description": _CAP_DESC("能力侧审批轨标记：与安全控制中心审批轨联动（子代理 interrupt_on 继承父级配置）。",
                              "关闭后子代理规格不继承 interrupt_on 审批中断点。",
                              "安全控制中心的审批轨开关独立生效。"), "confirm_required": False},
    {"capability_id": "prompt_caching", "title": "提示词缓存", "risk_level": "yellow",
     "physical_blocked": True, "blocked_reason": "Anthropic 专属特性：当前模型（DeepSeek/GLM）不支持显式 cache_control 断点",
     "description": _CAP_DESC("Anthropic 原生提示词缓存断点（cache_control）。",
                              "物理不可用：当前模型不支持，装配恒跳过。",
                              "DeepSeek 服务端前缀缓存自动生效（批5-C2/C3 已治理）。"), "confirm_required": True},
    {"capability_id": "video", "title": "视频能力", "risk_level": "yellow",
     "physical_blocked": True, "blocked_reason": "域无关能力：业务问答平台无视频输入/输出场景",
     "description": _CAP_DESC("多模态视频输入处理（deepagents 预留）。",
                              "物理不可用：平台无视频场景，装配恒跳过。",
                              "无剩余防线需求。"), "confirm_required": True},
    {"capability_id": "local_shell", "title": "本地 Shell", "risk_level": "yellow",
     "physical_blocked": True, "blocked_reason": "安全红线：服务端任意命令执行不可开放（execute 工具已在排除清单）",
     "description": _CAP_DESC("本地 Shell 执行工具（execute）。",
                              "物理禁用：安全红线，execute 在 HarnessProfile 排除清单且 backend 非 Sandbox 协议。",
                              "数据查询全部走 MCP 受控工具（SELECT-only + 守卫面）。"), "confirm_required": True},
    {"capability_id": "sandbox", "title": "沙箱执行", "risk_level": "yellow",
     "physical_blocked": True, "blocked_reason": "安全红线：SandboxBackend 未接入（无 sandbox-executor 后端绑定）",
     "description": _CAP_DESC("SandboxBackend 协议接入（代码执行沙箱）。",
                              "物理不可用：未接入沙箱后端，装配恒跳过。",
                              "业务问答不需要沙箱执行；数据分析走 SQL 受控链路。"), "confirm_required": True},
    {"capability_id": "tool_availability", "title": "工具白名单", "risk_level": "red",
     "params": {"allowed": _w1_default_allowed()},
     "description": _CAP_DESC("HarnessProfile 工具白名单打勾制（W-1 反转语义：没打勾即禁，框架升级新增工具天然免疫）——",
                              "调整 allowed 会触发 version+1 重建 Agent（下个请求生效）；取消业务工具走 🔴 风险确认。",
                              "read_file/ls/task 物理锁定不可取消（技能渐进披露/文件浏览/子代理命脉）；grep/glob/write_file/edit_file/execute 安全红线不在勾选域。"), "confirm_required": True},
    {"capability_id": "decision_gate", "title": "下一步判断闸门", "risk_level": "yellow",
     "seed_enabled": False,  # W-4a：代码基准=关（env TUPU_DECISION_GATE=1 为启动兜底；管理页可开）
     "params": {"scope_tools": ["execute_sql", "execute_doris_sql", "execute_entity_api", "execute_api_sql"]},
     "description": _CAP_DESC("DecisionGate 装卸开关（W-4a）+ 范围强校验工具集（W-4b）：工具调用前强制同轮「下一步判断」+数据工具客户名范围校验。",
                              "TUPU_DECISION_GATE=1 环境变量为启动兜底（恒开）；未设环境变量时以本开关为准（默认关=代码基准）。",
                              "scope_tools 可配置（⊆工具勾选域且非空）；SkillPolicy 站本体安全红线不可关，不在此列。"), "confirm_required": True},
    {"capability_id": "locate_budget", "title": "定位预算", "risk_level": "yellow",
     "params": {"generic": 8, "scenario": 14},
     "description": _CAP_DESC("定位类工具两级预算闸门（L1 同参去重+L2 总预算 generic 8/场景 14，P0-COUNT 死循环防护）——"
                              "参数可调（generic/scenario），关闭后定位类工具零预算零去重。",
                              "关闭后死循环防护消失（generic COUNT 题曾同参 search×28+batch×12 交替 163s 打结）；"
                              "极速模式保留开启（死循环防护非权限类）。",
                              "环境变量 TUPU_LOCATE_BUDGET/TUPU_LOCATE_BUDGET_SCENARIO 保留为缺省兜底；"
                              "读策略失败 fail-safe 回落环境变量默认（预算保持开）。"), "confirm_required": False},
]


def _seed_capability_policies(db: Session):
    """能力开关中心基线种子（幂等）。

    空表 -> 全量 seed；非空 -> **增量补种**：仅补 seed 中缺失的 capability_id
    （批13-J 收尾：已有库自动补 tool_availability 等新能力行，不覆盖管理员已有配置）；
    并把历史能力项 tool_exclusions 迁移为 tool_availability（定稿能力项名统一）。
    """
    from ..models.base import CapabilityPolicy
    # 能力项名迁移（2026-08-24 定稿对齐）：tool_exclusions -> tool_availability
    try:
        from sqlalchemy import text
        db.execute(text(
            "UPDATE capability_policies SET capability_id='tool_availability' "
            "WHERE capability_id='tool_exclusions'"))
        db.commit()
    except Exception:
        db.rollback()
    if not db.query(CapabilityPolicy).first():
        for p in CAPABILITY_POLICY_SEED:
            db.add(CapabilityPolicy(
                capability_id=p["capability_id"], title=p["title"],
                # seed_enabled=False 的能力项（如 decision_gate）种子即关——代码基准；其余默认全开
                enabled=p.get("seed_enabled", True),
                params=p.get("params"), risk_level=p.get("risk_level", "yellow"),
                description=p.get("description"), confirm_required=p.get("confirm_required", True),
                physical_blocked=p.get("physical_blocked", False),
                blocked_reason=p.get("blocked_reason"),
                version=1,
            ))
        db.commit()
        return
    # 增量补种：缺失的 capability_id 补齐（已有行不动）
    existing_ids = {row.capability_id for row in db.query(CapabilityPolicy.capability_id).all()}
    added = 0
    for p in CAPABILITY_POLICY_SEED:
        if p["capability_id"] in existing_ids:
            continue
        db.add(CapabilityPolicy(
            capability_id=p["capability_id"], title=p["title"],
            enabled=p.get("seed_enabled", True),  # W-4a：decision_gate 种子即关（代码基准）
            params=p.get("params"), risk_level=p.get("risk_level", "yellow"),
            description=p.get("description"), confirm_required=p.get("confirm_required", True),
            physical_blocked=p.get("physical_blocked", False),
            blocked_reason=p.get("blocked_reason"),
            version=1,
        ))
        added += 1
    if added:
        db.commit()
        logger.info(f"[CapabilitySeed] 增量补种 {added} 个能力: "
                    + ", ".join(p["capability_id"] for p in CAPABILITY_POLICY_SEED
                                if p["capability_id"] not in existing_ids))
    # 件②（2026-09-09 剧本定位提速）一次性同步：entity_locator 子代理 tools 增列
    # search_entities_batch。增量补种不覆盖已有行（防吃掉管理员配置），存量库 subagents
    # 行 params 仍是旧 specs JSON——此处仅对该行 params 内 name=entity_locator 的 spec
    # 的 tools 缺失时增列（幂等：已含即零写入；params 为 JSON 列，ORM 读出 dict 原位改后重赋值置脏）。
    try:
        _sub = db.query(CapabilityPolicy).filter(
            CapabilityPolicy.capability_id == "subagents").first()
        if _sub is not None:
            # deepcopy 后改再赋：JSON 列原位改同一对象再赋回自身，flush 判等会跳过该列 UPDATE
            # （实测：version 写入而 params 不落库）。tool_availability 块的 dict() 浅拷贝同理可写。
            import copy as _copy
            _params = _copy.deepcopy(_sub.params) if isinstance(_sub.params, dict) else None
            _changed = False
            for _spec in ((_params or {}).get("specs") or []):
                if isinstance(_spec, dict) and _spec.get("name") == "entity_locator":
                    _tools = [t for t in (_spec.get("tools") or []) if isinstance(t, str)]
                    if "search_entities_batch" not in _tools:
                        _tools.append("search_entities_batch")
                        _spec["tools"] = _tools
                        _changed = True
            if _changed:
                _sub.params = _params
                _sub.version = (_sub.version or 1) + 1
                db.commit()
                logger.info("[CapabilitySeed] entity_locator 子代理 tools 增列 search_entities_batch"
                            "（件②一次性同步，version+1 触发重装配）")
    except Exception as _loc_e:
        db.rollback()
        logger.warning(f"[CapabilitySeed] entity_locator tools 增列跳过（不影响启动）: {_loc_e}")
    # 件②（2026-09-09）一次性同步②：tool_availability 白名单存量行补勾 search_entities_batch。
    # 背景：GENERIC_ALLOWED_TOOLS 增列后，存量库该行 params.allowed 是行创建时的勾选域全勾
    # 快照（不含后加入的工具），W-1 换算 excluded = 勾选域 - allowed 会把新工具排除——
    # test_13w「默认全勾→excluded=红线5件」不变式实证此缺口。仅对本次新增工具名补勾
    # （该行创建时它尚不存在，不存在管理员故意取消的情形；不做通用机制，未来新工具
    # 默认开/关由届时决策）。幂等：已含即零写入。
    try:
        _ta = db.query(CapabilityPolicy).filter(
            CapabilityPolicy.capability_id == "tool_availability").first()
        if _ta is not None:
            _tp = dict(_ta.params or {})
            _allowed = _tp.get("allowed")
            if isinstance(_allowed, list) and "search_entities_batch" not in _allowed:
                _tp["allowed"] = sorted({t for t in _allowed if isinstance(t, str)}
                                        | {"search_entities_batch"})
                _ta.params = _tp
                _ta.version = (_ta.version or 1) + 1
                db.commit()
                logger.info("[CapabilitySeed] tool_availability 白名单补勾 search_entities_batch"
                            "（件②一次性同步，version+1 触发重装配）")
    except Exception as _ta_e:
        db.rollback()
        logger.warning(f"[CapabilitySeed] tool_availability 补勾跳过（不影响启动）: {_ta_e}")
    # 批13-W W-1：黑名单->白名单启动迁移（params 含旧 excluded 键 -> 换算 allowed 写回，零行为变化）
    try:
        from ..services.capability_config import migrate_tool_exclusions_to_allowlist
        _n = migrate_tool_exclusions_to_allowlist(db)
        if _n:
            logger.info(f"[CapabilitySeed] W-1 白名单迁移完成（{_n} 行）")
    except Exception as _mig_e:
        logger.warning(f"[CapabilitySeed] W-1 白名单迁移跳过（不影响启动）: {_mig_e}")


def _seed_expert_profiles(db: Session):
    """专家地基①：wenshu 种子卡（不存在则种，幂等——不覆盖管理员已有配置）。"""
    from ..models.base import ExpertProfile
    from ..services.expert_config import default_wenshu_card
    try:
        if db.query(ExpertProfile).filter(ExpertProfile.expert_id == "wenshu").first() is None:
            c = default_wenshu_card()
            db.add(ExpertProfile(
                expert_id=c["expert_id"], name=c["name"], tagline=c["tagline"],
                enabled=True, entry_kind="chat", system_prompt=c["system_prompt"],
                tools=c["tools"], skills=c["skills"], memory=c["memory"],
                knowledge_sources=c["knowledge_sources"], llm_connection_id=None,
                icon=c["icon"], description=c["description"], ui_config=c["ui_config"],
                version=1))
            db.commit()
            logger.info("[ExpertSeed] wenshu 种子卡已落库（tools=活注册表 %d 件）" % len(c["tools"]))
    except Exception as e:
        db.rollback()
        logger.warning(f"[ExpertSeed] 种子跳过（不影响启动）: {e}")


def _sync_scenario_skills(db: Session):
    """将文件式场景剧本(scenarios/*/SKILL.md)同步到 skills 表，使其在技能管理页可见。

    SkillManagerV2 调 GET /api/v2/skills 只查 DB skills 表；场景剧本是文件式（data/skills/scenarios/*/SKILL.md），
    无 DB 记录 -> 不展示。这里在启动时 upsert，status='published'。
    skill_code 带斜杠（"scenarios/<name>"），skill_storage._skill_path 会解析到现有目录，所有文件 API 免改。
    """
    from pathlib import Path
    from ..core.skill_storage import get_skill_storage
    from ..models.skill import Skill

    storage = get_skill_storage()
    scen_dir = Path(storage.root) / "scenarios"
    if not scen_dir.exists():
        return
    for md in scen_dir.glob("*/SKILL.md"):
        skill_code = f"scenarios/{md.parent.name}"
        meta = storage.parse_skill_md(skill_code)
        existing = db.query(Skill).filter(Skill.skill_code == skill_code).first()
        name = meta.get("name") or md.parent.name
        desc = meta.get("description")
        storage_path = str(storage._skill_path(skill_code))
        if existing:
            # 更新 name/description（用户可能编辑过 SKILL.md）
            existing.name = name
            if desc:
                existing.description = desc
            existing.storage_path = storage_path
            existing.status = "published"
        else:
            db.add(Skill(
                skill_code=skill_code,
                name=name,
                description=desc,
                skill_type=meta.get("skill_type") or "claude",
                status="published",
                storage_path=storage_path,
                app_type="chat",
                target_menu="chat",
            ))
    db.commit()


def init_db(db: Session):
    """数据库初始化（仅技能类型，不建概念/实体种子数据）。

    图谱只读主数据建模和业务活动建模维护的实体，不做内部初始化。
    """
    # 初始化默认技能类型
    from ..models.skill import SkillType
    if not db.query(SkillType).first():
        default_types = [
            SkillType(type_code="natural", name="自然语言", icon="ExperimentOutlined", color="#10b981", sort_order=1, ext="txt"),
            SkillType(type_code="python", name="Python", icon="CodeOutlined", color="#3b82f6", sort_order=2, ext="py"),
            SkillType(type_code="sql", name="SQL", icon="DatabaseOutlined", color="#f59e0b", sort_order=3, ext="sql"),
            SkillType(type_code="http", name="HTTP", icon="GlobalOutlined", color="#8b5cf6", sort_order=4, ext="yaml"),
            SkillType(type_code="mixed", name="混合", icon="ApiOutlined", color="#ec4899", sort_order=5, ext="yaml"),
        ]
        for t in default_types:
            db.add(t)
        db.commit()

    # 同步文件式场景剧本到 skills 表（技能管理页可见）
    _sync_scenario_skills(db)

    # 安全控制中心基线策略（幂等：仅表空时插入）
    _seed_guard_policies(db)

    # 能力开关中心基线策略（批13-Q，幂等）
    _seed_capability_policies(db)

    # 专家地基①：wenshu 种子卡（幂等：不存在则种）
    _seed_expert_profiles(db)

    # 批13-C：金标表兼容补列（已有库缺 engine/hit_count/last_hit_at；create_all 不改已有表）
    _ensure_golden_columns(db)

    # 专家地基①（spec §九步骤 3）：kg_run_events + expert_id 观测列（失败不阻启动）
    _ensure_expert_column(db)

    # 附件四 A-1：专家卡 suggestions/params 两列（已有库缺列补齐；create_all 不改已有表）
    _ensure_expert_card_columns(db)

    # ⑥-2a（spec D3）：expert 资源公共语义种子（幂等）——wenshu→role viewer→use
    # （登录兜底 viewer→全员可用）；tutor 等不种=默认私有（显式赋权才见）。
    _seed_expert_acl(db)


def _seed_expert_acl(db: Session):
    from ..models.auth import ResourceACL
    row = (db.query(ResourceACL)
           .filter(ResourceACL.resource_type == "expert",
                   ResourceACL.resource_id == "wenshu",
                   ResourceACL.principal_type == "role",
                   ResourceACL.principal_id == "viewer")
           .first())
    if row is None:
        db.add(ResourceACL(resource_type="expert", resource_id="wenshu",
                           principal_type="role", principal_id="viewer",
                           actions=["use"], granted_by="seed"))
        db.commit()


def _ensure_expert_card_columns(db: Session):
    """附件四 A-1：kg_expert_profiles +suggestions/params（JSON NULL，幂等——列存在则跳过）。"""
    from sqlalchemy import text
    for col, ddl in (("suggestions", "JSON"),
                     ("params", "JSON")):
        try:
            has = db.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE "
                "TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kg_expert_profiles' "
                f"AND COLUMN_NAME = '{col}'")).scalar()
            if not has:
                db.execute(text(f"ALTER TABLE kg_expert_profiles ADD COLUMN {col} {ddl} NULL"))
                db.commit()
                logger.info(f"[附件四A-1] kg_expert_profiles.{col} 列已加")
        except Exception as e:
            db.rollback()
            logger.warning(f"[附件四A-1] kg_expert_profiles.{col} 补列失败（不阻启动）: {e}")


def _ensure_expert_column(db: Session):
    """专家地基①（spec §九步骤 3）：kg_run_events + expert_id（NOT NULL DEFAULT 'wenshu'——
    MySQL 8 自动回填存量行，独立 UPDATE 省略；列存在则跳过，幂等）。"""
    try:
        from sqlalchemy import text
        has = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE "
            "TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kg_run_events' "
            "AND COLUMN_NAME = 'expert_id'")).scalar()
        if not has:
            db.execute(text(
                "ALTER TABLE kg_run_events ADD COLUMN expert_id VARCHAR(64) "
                "NOT NULL DEFAULT 'wenshu'"))
            db.commit()
            logger.info("[专家地基] kg_run_events.expert_id 列已加（存量行自动回填 wenshu）")
    except Exception as e:
        db.rollback()
        logger.warning(f"[专家地基] expert_id 列确保失败（观测列缺失不阻主链路）: {e}")


def _ensure_golden_columns(db: Session):
    """批13-C：kg_golden_qa_set 增列兼容（engine/hit_count/last_hit_at）+ engine 值回填。

    直通需 engine 列（设计字段核对项）：NULL 时按 SQL 前缀推断——
    internal./test_db./pg_tupu. -> doris 联邦，其余 -> physical。失败仅告警不阻断启动。
    """
    try:
        from sqlalchemy import text
        _want = {
            "engine": "VARCHAR(16) NULL",
            "hit_count": "INTEGER NULL DEFAULT 0",
            "last_hit_at": "DATETIME NULL",
        }
        _existing = {r[0] for r in db.execute(text(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kg_golden_qa_set'")).fetchall()}
        for col, ddl in _want.items():
            if col not in _existing:
                db.execute(text(f"ALTER TABLE kg_golden_qa_set ADD COLUMN {col} {ddl}"))
                logger.info(f"[InitDB] kg_golden_qa_set 补列 {col}")
        db.commit()
        # engine 值回填（仅 NULL 行；与 _exec_for_digest 同一前缀口径）
        db.execute(text(
            "UPDATE kg_golden_qa_set SET engine='doris' "
            "WHERE engine IS NULL AND (expected_sql LIKE '%internal.%' OR expected_sql LIKE '%test_db.%' OR expected_sql LIKE '%pg_tupu.%')"))
        db.execute(text(
            "UPDATE kg_golden_qa_set SET engine='physical' WHERE engine IS NULL"))
        db.commit()
    except Exception as _e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning(f"[InitDB] 金标表补列/回填失败（忽略）: {_e}")
