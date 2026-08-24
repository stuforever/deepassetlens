"""query_contract.py - 受控执行契约（受控 Skill 问答平台 v2，设计 §5）

路由后立刻创建契约，之后 Agent、Policy、前端都只认这份契约：
- allowed_tools / forbidden_tools：本次允许与禁止的工具；
- template_ids：本次允许绑定的 SQL 模板；
- scope：客户/时间/实体范围（customer_names 精确集合，commitment）；
- selected_engine / engine_reason：三引擎（Doris/DuckDB/物理表）唯一选择与原因；
- output_mode / stop_when：输出模式与终止条件；
- _runtime：本次运行的**可变**状态（引擎是否锁定、是否已拿到数据结果），供 Policy 中间件读写。
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 默认只读通用能力（未命中场景时的低权限模式工具集）
# P0 整改（架构演进对齐）：工具层已把统一 kg_api 拆成 16 个单一职责 MCP 工具（app/mcp_server.py），
# 此处白名单必须与真实注册工具名一致，否则模型只能调白名单里不存在的幽灵工具 -> generic 模式死锁。
# 安全不降级：ABSOLUTE_FORBIDDEN_TOOLS 仍全局硬禁；执行类仍走 validate_safe_sql / ScopeChecker / 引擎锁定。
GENERIC_ALLOWED_TOOLS = frozenset({
    # 定位类（只读元数据）
    "fetch_l1_l2_tree", "validate_l2", "fetch_subgraph",
    "search_entities", "search_concepts", "get_entity_relations", "list_tables",
    # 校验类（只读）
    "validate_attributes", "fetch_join_expr", "validate_safe_sql",
    # 取样类（只读，G3：分类/状态/类型列写 WHERE 前先取真实枚举值）
    "sample_column_values",
    # 源模式确认
    "get_entity_source_mode", "batch_entity_source_mode",
    # 执行类（受 validate_safe_sql / ScopeChecker / 引擎锁定闸门保护）
    "execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api",
    # 只读技能文件（deepagents 框架工具，非 MCP）
    "read_file",
})
# 绝对禁止的工具（任何契约下都不可调用）
ABSOLUTE_FORBIDDEN_TOOLS = frozenset({
    "task",        # 子 Agent
    "write_file",  # 写文件
    "edit_file",   # 改文件
    "execute",     # Shell
    "grep",        # 搜文件内容
    "glob",        # 列文件
})

# 三引擎 -> 允许的数据工具（引擎一旦锁定，只允许对应工具）
ENGINE_TO_TOOLS: Dict[str, List[str]] = {
    "doris": ["execute_doris_sql"],
    "duckdb": ["execute_api_sql", "execute_entity_api"],
    "physical": ["execute_sql"],
}
# 数据工具集合（用于 stop_when / 引擎一致性判断）
DATA_TOOLS = frozenset({"execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api"})

# M3（融合设计 §5.1）：generic 模式自评 rubric（RubricMiddleware 激活文案；scenario 模板已保证结构，rubric=None）
# S1（L3）：第 5 条补分布/统计类结果必须聚合视图，禁止明细全表。
GENERIC_RUBRIC = (
    "本回答必须满足：\n"
    "1. 数字必须来自工具返回结果，禁止编造或心算；\n"
    "2. 注明统计口径：实体表、时间范围、过滤条件；\n"
    "3. 结果为空或验证失败时明示原因，不得给猜测值；\n"
    "4. 直接回答用户问题本身的量词与维度（总数/ TopN/占比…）；\n"
    "5. 分布/统计类问题的结果必须是聚合视图（GROUP BY 维度列），不得返回明细全表。"
)


@dataclass
class QueryContract:
    """单次运行受控契约。字段一旦建立即不可由模型改写；仅 _runtime 由代码更新。"""

    run_id: str
    skill_id: str
    skill_version: str
    workflow_step: str
    allowed_tools: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    template_ids: List[str] = field(default_factory=list)          # 形如 "skill:step/模板名"
    scope: Dict[str, Any] = field(default_factory=dict)            # {customer_names, commitment, source}
    selected_engine: Optional[str] = None                          # doris | duckdb | physical | None
    engine_reason: Optional[str] = None
    output_mode: str = "single_result_table"
    stop_when: List[str] = field(default_factory=list)
    route_reason: str = ""
    route_type: str = "scenario"                                   # scenario | generic | ...
    rubric: Optional[str] = None                                   # M3 DA-2：自评闸门 rubric（generic 默认文案；scenario 为 None）
    aggregate_intent: Optional[Dict[str, Any]] = None              # S1（稳定性攻坚 L1）：聚合分布意图标记 {dimension_hint, required_shape}
    clarify_required: bool = False                                 # S2（金标扩容）：路由层歧义检测 -> 意图不明确，须澄清而非乱查
    multi_engine: bool = False                                     # 批4/场景迁移：多数据源逐源分发（引擎不唯一）
    forbid_markdown_detail_table: bool = True                      # 输出契约：结果已推前端时禁 Markdown 明细表
    entity_engine_map: Dict[str, str] = field(default_factory=dict)  # 实体 -> 引擎 真实映射（源模式工具返回）
    # 评审 P1-1（二轮）：多引擎必达数据源（Skill 显式声明 required_sources），终止按实体/角色判断
    required_entities: List[str] = field(default_factory=list)
    _runtime: Dict[str, Any] = field(default_factory=dict)         # {engine_locked, result_obtained, violations, confirmed_engines, ...}

    # ------------------------------------------------------------------
    # 构造
    # ------------------------------------------------------------------
    @classmethod
    def from_step(cls, skill_id: str, skill_version: str, step: Any, *,
                  scope: Optional[Dict[str, Any]] = None,
                  route_reason: str = "", route_type: str = "scenario",
                  multi_engine: bool = False,
                  forbid_markdown_detail_table: bool = True,
                  output_mode: Optional[str] = None,
                  required_entities: Optional[List[str]] = None) -> "QueryContract":
        """按 Skill 定义 + 命中步骤构造契约。step 为 skill_catalog.StepDefinition。

        output_mode 优先级：显式参数 > 步骤级 step.output_mode > 类默认 single_result_table。
        required_entities：多引擎技能声明必达数据源（SKILL.md required_sources），
        终止按实体/角色判断而非按"已确认引擎"（评审 P1-1 二轮）。
        """
        # read_file 永久允许（只读 /skills/** 子文件，模型须读 SKILL.md 与步骤模板/参考）
        allowed = list(dict.fromkeys(list(step.allowed_tools) + ["read_file"]))
        c = cls(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            skill_id=skill_id,
            skill_version=skill_version,
            workflow_step=step.id,
            allowed_tools=allowed,
            template_ids=[f"{skill_id}:{t}" for t in step.templates],
            scope=dict(scope or {"customer_names": [], "commitment": "none", "source": "user_input"}),
            output_mode=output_mode or step.output_mode or "single_result_table",
            stop_when=list(step.stop_when),
            route_reason=route_reason,
            route_type=route_type,
            multi_engine=multi_engine,
            forbid_markdown_detail_table=forbid_markdown_detail_table,
            required_entities=[str(e) for e in (required_entities or []) if e],
            _runtime={
                "engine_locked": False, "result_obtained": False, "violations": 0,
                "confirmed_engines": [],
                "confirmed_entities": [], "completed_entities": [],
                "terminal": not bool(step.allowed_next),  # 无后继步骤 = 拿到结果即终止
            },
        )
        # 契约内 always 禁用绝对禁止工具（模型/技能声明只能加不能减）
        forbidden = [t for t in ABSOLUTE_FORBIDDEN_TOOLS if t not in c.allowed_tools]
        c.forbidden_tools = forbidden
        return c

    @classmethod
    def generic(cls, *, scope: Optional[Dict[str, Any]] = None,
                route_reason: str = "", aggregate_intent: Optional[Dict[str, Any]] = None,
                clarify_required: bool = False) -> "QueryContract":
        """未命中场景时的低权限只读通用契约（禁止写入/task/Shell）。

        aggregate_intent（S1 稳定性攻坚 L1）：路由层识别分布/占比/构成类触发词后注入，
        契约追加受控指令（禁止返回明细全表）+ 结果层硬校验钩子。
        clarify_required（S2 金标扩容）：路由层歧义检测命中 -> 意图不明确，收缩工具集
        为空（模型无法执行任何数据查询），契约指令要求仅输出一句澄清问题。
        """
        c = cls(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            skill_id="__generic__",
            skill_version="1.0",
            workflow_step="__generic__",
            allowed_tools=[] if clarify_required else sorted(GENERIC_ALLOWED_TOOLS),
            forbidden_tools=sorted(ABSOLUTE_FORBIDDEN_TOOLS),
            scope=dict(scope or {"customer_names": [], "commitment": "none", "source": "user_input"}),
            output_mode="default",
            route_reason=route_reason or "未命中场景剧本，进入低权限只读通用模式",
            route_type="generic",
            rubric=GENERIC_RUBRIC,
            aggregate_intent=aggregate_intent,
            clarify_required=clarify_required,
            _runtime={"engine_locked": False, "result_obtained": False, "violations": 0},
        )
        return c

    # ------------------------------------------------------------------
    # 运行期更新（仅代码调用，模型不可改）
    # ------------------------------------------------------------------
    def lock_engine(self, engine: str, reason: str) -> None:
        """根据 batch_entity_source_mode 真实返回锁定唯一引擎（多引擎技能走 confirm_engines）。"""
        if self.multi_engine:
            self.confirm_engines([engine], reason)
            return
        self.selected_engine = engine
        self.engine_reason = reason
        self._runtime["engine_locked"] = True
        # 引擎确认后，其他查询工具立即失效：allowed_tools 收窄为 该引擎工具 + 非数据工具
        keep = [t for t in self.allowed_tools if t not in DATA_TOOLS]
        self.allowed_tools = keep + ENGINE_TO_TOOLS.get(engine, [])

    def confirm_engines(self, engines: List[str], reason: str,
                        entity_engine_map: Optional[Dict[str, str]] = None) -> None:
        """多引擎技能：按 batch/单实体 真实返回确认数据源模式集合（逐源分发，引擎不唯一）。

        引擎确认后收窄 allowed_tools 为已确认引擎工具并集 + 非数据工具；
        再次确认（逐实体）会**并入**新引擎，重复值由集合自然去重（评审 P1-1 修复）。
        """
        confirmed = set(self._runtime.get("confirmed_engines") or [])
        confirmed.update(engines or [])
        self._runtime["confirmed_engines"] = sorted(confirmed)
        self.engine_reason = reason or "；".join(sorted(confirmed))
        # 实体 -> 引擎 真实映射（batch items / 单实体返回），供前端与审计使用
        if entity_engine_map:
            self.entity_engine_map.update({str(k): str(v) for k, v in entity_engine_map.items()})
        keep = [t for t in self.allowed_tools if t not in DATA_TOOLS]
        engine_tools: List[str] = []
        for e in sorted(confirmed):
            for t in ENGINE_TO_TOOLS.get(e, []):
                if t not in engine_tools:
                    engine_tools.append(t)
        self.allowed_tools = keep + engine_tools
        # 多引擎复合终止（旧语义保留作回退）：已确认引擎即必达引擎
        self._runtime["required_engines"] = sorted(confirmed)

    def confirm_entities(self, entity_codes: List[str]) -> None:
        """多引擎：记录已确认 source_mode 的实体（confirmed_entities，去重并入）。"""
        codes = [str(c) for c in (entity_codes or []) if c]
        if not codes:
            return
        conf = set(self._runtime.setdefault("confirmed_entities", []))
        conf.update(codes)
        self._runtime["confirmed_entities"] = sorted(conf)

    def mark_entity_result(self, entity_code: Optional[str]) -> None:
        """多引擎：记录某实体已取到结果（completed_entities，去重并入）。

        评审 P1-1（二轮）：终止按**实体/数据角色**判断 —— 两个实体同引擎时，
        第一次查询只完成该实体，不能误判该引擎已全部完成。
        """
        if not entity_code:
            return
        done = set(self._runtime.setdefault("completed_entities", []))
        done.add(str(entity_code))
        self._runtime["completed_entities"] = sorted(done)

    def add_entity_engines(self, entity_engine_map: Dict[str, str]) -> None:
        """合并实体 -> 引擎映射（不改变已确认引擎集合）。"""
        if entity_engine_map:
            self.entity_engine_map.update({str(k): str(v) for k, v in entity_engine_map.items()})

    def confirmed_engines(self) -> List[str]:
        """已确认的数据源模式（多引擎技能用）。"""
        return list(self._runtime.get("confirmed_engines") or [])

    def engine_for_tool(self, tool: str) -> Optional[str]:
        """数据工具 -> 所属引擎（reverse ENGINE_TO_TOOLS）。"""
        for e, tools in ENGINE_TO_TOOLS.items():
            if tool in tools:
                return e
        return None

    def mark_engine_result(self, engine: str) -> None:
        """多引擎：记录某引擎已取到结果（result_by_engine，回退语义用）。"""
        rb = self._runtime.setdefault("result_by_engine", {})
        rb[str(engine)] = True

    def multi_engine_done(self) -> bool:
        """多引擎复合终止判定。

        优先按**实体/数据角色**（required_entities 声明，Skill required_sources）——
        completed_entities 覆盖 required_entities 才算两源取齐；
        未声明时回退到引擎语义（required_engines = 已确认引擎全部取到结果）。
        """
        if not self.multi_engine:
            return False
        req = [e for e in (self._runtime.get("required_entities") or self.required_entities) if e]
        if req:
            done = set(self._runtime.get("completed_entities") or [])
            return set(req) <= done
        rb = self._runtime.get("result_by_engine") or {}
        required = self._runtime.get("required_engines") or []
        if not required:
            return False
        return all(rb.get(e) for e in required)

    @property
    def stop_reached(self) -> bool:
        return bool(self._runtime.get("stop_reached"))

    def set_stop_reached(self) -> None:
        """多引擎取齐/终端步骤取到结果 -> 终止（禁止继续检索）。"""
        self._runtime["stop_reached"] = True
        self._runtime["terminal"] = True
        # 终止后数据工具全部移除（模型无法再查）
        self.allowed_tools = [t for t in self.allowed_tools if t not in DATA_TOOLS]

    def mark_result(self) -> None:
        self._runtime["result_obtained"] = True

    def record_violation(self) -> int:
        self._runtime["violations"] = self._runtime.get("violations", 0) + 1
        return self._runtime["violations"]

    # ------------------------------------------------------------------
    # 判定辅助（供 Policy 中间件）
    # ------------------------------------------------------------------
    @property
    def engine_locked(self) -> bool:
        return bool(self._runtime.get("engine_locked"))

    @property
    def result_obtained(self) -> bool:
        return bool(self._runtime.get("result_obtained"))

    def is_data_tool(self, tool: str) -> bool:
        return tool in DATA_TOOLS

    def allows(self, tool: str) -> bool:
        return tool in self.allowed_tools and tool not in self.forbidden_tools

    # ------------------------------------------------------------------
    # 序列化（SSE / 前端展示用）
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "workflow_step": self.workflow_step,
            "allowed_tools": list(self.allowed_tools),
            "forbidden_tools": list(self.forbidden_tools),
            "template_ids": list(self.template_ids),
            "scope": dict(self.scope),
            "selected_engine": self.selected_engine,
            "engine_reason": self.engine_reason,
            "output_mode": self.output_mode,
            "stop_when": list(self.stop_when),
            "route_reason": self.route_reason,
            "route_type": self.route_type,
            "rubric": self.rubric,
            "aggregate_intent": self.aggregate_intent,  # S1（L1）：聚合分布意图（前端证据/契约卡观测）
            "clarify_required": self.clarify_required,  # S2：歧义需澄清（路由层标记）
            "multi_engine": self.multi_engine,
            "forbid_markdown_detail_table": self.forbid_markdown_detail_table,
            "confirmed_engines": list(self._runtime.get("confirmed_engines") or []),
            "entity_engine_map": dict(self.entity_engine_map),
            "result_by_engine": dict(self._runtime.get("result_by_engine") or {}),
            "stop_reached": bool(self._runtime.get("stop_reached")),
            "required_engines": list(self._runtime.get("required_engines") or []),
            "required_entities": list(self._runtime.get("required_entities") or self.required_entities),
            "confirmed_entities": list(self._runtime.get("confirmed_entities") or []),
            "completed_entities": list(self._runtime.get("completed_entities") or []),
        }


# ----------------------------------------------------------------------
# 批2-E：指引预载（省 read_file 技能轮）
# ----------------------------------------------------------------------
# 规则意图分类命中 sql-query/SKILL.md 对应小节，摘录 5-8 行注入契约消息，
# 模型直接参考无需 read_file(/skills/sql-query/...)。模块加载时解析一次并缓存。
_SKILL_SQL_QUERY_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "skills", "sql-query", "SKILL.md"))
_GUIDANCE_SECTIONS: Optional[Dict[str, str]] = None
# 意图规则：(小节标题前缀, 触发词) 按序判定；命中即摘录对应小节
_GUIDANCE_RULES = (
    ("聚合类", ("数量", "总数", "多少", "统计", "几个", "平均", "总和", "总计", "分组", "占比", "分布", "比例", "百分比")),
    ("排名类", ("排名", "前", "最大", "最多", "最少", "top", "Top")),
    ("趋势类", ("同比", "环比", "趋势", "逐月", "逐季", "增长率")),
    ("对比类", ("对比", "相比", "哪个多", "哪个少")),
    ("质检类", ("空值", "重复", "异常", "质检", "缺失", "完整性")),
)


def _load_guidance_sections() -> Dict[str, str]:
    """解析 sql-query/SKILL.md，按 `### ` 小节切分缓存（标题 -> 小节正文）。"""
    global _GUIDANCE_SECTIONS
    if _GUIDANCE_SECTIONS is not None:
        return _GUIDANCE_SECTIONS
    sections: Dict[str, str] = {}
    try:
        with open(_SKILL_SQL_QUERY_PATH, encoding="utf-8") as f:
            text = f.read()
        cur: Optional[str] = None
        buf: List[str] = []
        for line in text.splitlines():
            if line.startswith("### "):
                if cur and buf:
                    sections[cur] = "\n".join(buf)
                cur = line[4:].strip()
                buf = []
            elif cur is not None:
                buf.append(line)
        if cur and buf:
            sections[cur] = "\n".join(buf)
    except Exception as _e:
        logger.warning(f"[指引预载] SKILL.md 解析失败: {_e}")
    _GUIDANCE_SECTIONS = sections
    return sections


def build_guidance_block(question: str, max_lines: int = 8) -> str:
    """规则意图分类 -> sql-query/SKILL.md 小节摘录（默认 ≤8 行）。无意图命中返回空串。"""
    q = (question or "").strip()
    if not q:
        return ""
    sections = _load_guidance_sections()
    if not sections:
        return ""
    picked: List[str] = []
    for _label, _words in _GUIDANCE_RULES:
        if any(w in q for w in _words):
            picked.append(_label)
    picked = list(dict.fromkeys(picked))
    if not picked:
        return ""
    lines = ["\n写法指引（摘自 sql-query 技能，直接参考无需 read_file）："]
    for _label in picked[:2]:  # 最多两节，控制注入体积
        # 规则标签（如「聚合类」）是 SKILL.md 小节标题前缀（如「聚合类（问数量/统计/占比/平均/分组）」），前缀匹配
        body = next((v.splitlines() for k, v in sections.items() if k.startswith(_label)), [])
        # 优先摘表格模板行（"用户说法" -> SQL 映射）与硬规则行；去表头分隔线
        _core = [l.strip() for l in body if l.strip() and not l.strip().startswith("|---")][:max_lines]
        if _core:
            lines.append(f"· {_label}：")
            lines.extend(_core)
    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


# ----------------------------------------------------------------------
# 批1-B：rubric 分档直通（示例锚定直通）
# ----------------------------------------------------------------------
# 示例锚定强度阈值：相似度 >= 该值时，已验证示例提供确定性保障（守卫+引擎锁定+金标回归），
# grader 边际价值≈0 且固定 +20~40s，故跳过 rubric 自评。环境变量 TUPU_RUBRIC_ANCHOR_SIM 可调。
EXAMPLE_ANCHOR_SIM = float(os.getenv("TUPU_RUBRIC_ANCHOR_SIM", "0.85"))


def apply_rubric_tier(contract: QueryContract) -> None:
    """示例锚定直通：有高分已验证示例锚定的 generic 查询跳过 rubric 自评。

    依据：模板/示例锚定的 SQL 已有确定性保障（守卫+引擎锁定+金标回归），grader 边际价值≈0
    且固定 +20~40s。未锚定查询保留自评。
    边界：聚合分布类问题（S1 的 P-A 不稳定源）**不豁免**——aggregate_intent 命中时仍需自评兜底。
    """
    if contract.route_type != "generic" or not contract.rubric:
        return
    if getattr(contract, "aggregate_intent", None):
        return  # S1：聚合分布正是自评兜底对象，不直通
    hits = (contract._runtime or {}).get("example_hits") or []
    if hits and max((h.get("score") or 0) for h in hits) >= EXAMPLE_ANCHOR_SIM:
        contract.rubric = None
        contract._runtime["rubric_skipped"] = "example_anchored"
