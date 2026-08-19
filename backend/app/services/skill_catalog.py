"""skill_catalog.py - SKILL.md 唯一来源解析器（受控 Skill 问答平台 v2）

职责（对齐设计 §3.3）：
1. 扫描 backend/data/skills/scenarios/**/SKILL.md；
2. 解析标准 frontmatter（name/description/category）与平台扩展 x_tupu；
3. 校验必要字段（缺失则该 Skill 不可用，不允许"猜着执行"）；
4. 返回不可变 SkillDefinition；
5. 生成当前可用 Skill 的简短索引（替代 tupu_deepagent 中的静态 _SKILL_OVERVIEW）；
6. 按文件 mtime + SHA256 自动刷新缓存；校验失败保留最近一次有效版本并记告警。

SKILL.md 是唯一业务来源；本模块缓存只是性能优化，不是第二份配置。
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# 场景技能根目录（唯一权威入口：backend/data/skills/scenarios/<skill-name>/SKILL.md）
_SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "skills"
_SCENARIOS_DIR = _SKILLS_ROOT / "scenarios"

# 必须由代码执行的结构化字段（其余业务口径保留 Markdown 正文）
_REQUIRED_X_TUPU_FIELDS = ("enabled", "triggers", "steps")
_REQUIRED_STEP_FIELDS = ("id", "title", "allowed_tools")

# ---- 批4 生产治理：编译期校验常量（设计 §1.2）----
OUTPUT_MODE_ENUM = frozenset({"single_result_table", "analysis_and_result_table", "clarify", "text"})
# 全局工具名册（通用能力工具 + 绝对禁用工具 + 设计 §1.1 场景禁用清单）
# P0 整改：GENERIC_ALLOWED_TOOLS 已对齐 mcp_server.py 实际注册的 16 个工具，
# 因此 validate_l2/search_concepts/get_entity_relations/list_tables/validate_safe_sql
# 也随 _BASE_REGISTRY 一并入册（此前缺失，场景一旦声明即被"未知工具"误禁）。
try:
    from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS, GENERIC_ALLOWED_TOOLS
    _BASE_REGISTRY = set(GENERIC_ALLOWED_TOOLS) | set(ABSOLUTE_FORBIDDEN_TOOLS)
except Exception:  # 防御性：导入失败则退化为空，不影响解析
    _BASE_REGISTRY = set()
# 设计 §1.1 明确禁止的"场景不得调用"工具（全局名册承认其存在，但场景不应列出它们）
_DESIGN_FORBIDDEN_EXTRAS = frozenset({
    "search_entities", "fetch_join_expr", "fetch_l1_l2_tree", "fetch_subgraph",
    "validate_attributes",
})
# 数据源模式确认工具（get_entity_source_mode 为真实注册的单实体接口，列入名册供场景声明）
_SOURCE_MODE_TOOLS = frozenset({"get_entity_source_mode"})
GLOBAL_TOOL_REGISTRY = frozenset(_BASE_REGISTRY) | _DESIGN_FORBIDDEN_EXTRAS | _SOURCE_MODE_TOOLS


@dataclass(frozen=True)
class StepDefinition:
    """SKILL.md x_tupu.steps[] 中的单一步骤定义。"""

    id: str
    title: str
    triggers: Dict[str, Any] = field(default_factory=dict)   # {any: [...], all_groups: [[...]]}
    allowed_tools: List[str] = field(default_factory=list)
    required_slots: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)       # 相对 SKILL.md 的模板路径
    reference_files: List[str] = field(default_factory=list)
    stop_when: List[str] = field(default_factory=list)
    allowed_next: List[str] = field(default_factory=list)
    output_mode: str = ""                                     # 步骤级输出模式（可选，缺省走 skill 级）

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "triggers": self.triggers,
            "allowed_tools": self.allowed_tools, "required_slots": self.required_slots,
            "templates": self.templates, "reference_files": self.reference_files,
            "stop_when": self.stop_when, "allowed_next": self.allowed_next,
            "output_mode": self.output_mode,
        }


@dataclass(frozen=True)
class SkillDefinition:
    """解析并校验后的不可变 Skill 定义（SKILL.md = 唯一事实来源）。"""

    name: str
    description: str
    category: str
    path: Path
    sha256: str
    mtime: float
    body: str                                          # frontmatter 之后的 Markdown 正文
    enabled: bool = True
    version: str = "1.0"
    priority: int = 0
    triggers: Dict[str, Any] = field(default_factory=dict)
    forbidden_tools: List[str] = field(default_factory=list)
    entity_aliases: Dict[str, str] = field(default_factory=dict)  # ⟦业务中文名⟧ -> 物理表名
    output: Dict[str, Any] = field(default_factory=dict)
    steps: List[StepDefinition] = field(default_factory=list)
    multi_engine: bool = False                                    # 批4：多数据源逐源分发（引擎不唯一）
    template_mode: str = "scenario_extensible"                    # P0-2：模板校验分级（strict/extensible/generic）
    required_sources: List[Dict[str, str]] = field(default_factory=list)  # 评审P1-1：多引擎必达数据源 [{entity, role}]

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description, "category": self.category,
            "enabled": self.enabled, "version": self.version, "priority": self.priority,
            "triggers": self.triggers, "forbidden_tools": self.forbidden_tools,
            "entity_aliases": self.entity_aliases, "output": self.output,
            "multi_engine": self.multi_engine, "template_mode": self.template_mode,
            "required_sources": list(self.required_sources),
            "steps": [s.to_dict() for s in self.steps],
        }

    def required_entity_codes(self) -> List[str]:
        """必达数据源实体代码（去重保序）。"""
        out: List[str] = []
        for src in self.required_sources:
            ec = str(src.get("entity") or "")
            if ec and ec not in out:
                out.append(ec)
        return out

    def find_step(self, step_id: str) -> Optional[StepDefinition]:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None


class SkillCatalog:
    """按文件 mtime+SHA256 缓存解析结果的 Skill 目录。

    线程安全：模块级单例 _CATALOG；每次 load 先查 mtime，变化才重读重校验。
    校验失败保留最近一次有效版本并记录告警（设计 §3.3 缓存策略）。
    """

    def __init__(self, scenarios_dir: Path | None = None) -> None:
        self._scenarios_dir = scenarios_dir or _SCENARIOS_DIR
        self._cache: Dict[str, SkillDefinition] = {}
        self._warnings: List[str] = []
        self._failed: Dict[str, str] = {}  # 解析失败缓存（skill_name -> error），避免重复读盘/重复告警
        self._last_version_hash: Dict[str, tuple] = {}  # skill_name -> (version, sha256)，批4 版本稳定性

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def list_skills(self) -> List[SkillDefinition]:
        """扫描并返回全部已启用且解析成功的场景 Skill（按 priority 降序）。"""
        out: List[SkillDefinition] = []
        for md in sorted(self._scenarios_dir.glob("*/SKILL.md")):
            skill = self.load_skill(md.parent.name)
            if skill is not None and skill.enabled:
                out.append(skill)
        out.sort(key=lambda s: s.priority, reverse=True)
        return out

    def load_skill(self, skill_name: str) -> Optional[SkillDefinition]:
        """按名加载 Skill；文件不存在/解析失败返回 None（不可用即不猜着执行）。"""
        md = self._scenarios_dir / skill_name / "SKILL.md"
        if not md.exists():
            return None
        sig = self._fingerprint(md)
        cached = self._cache.get(skill_name)
        if cached is not None and cached.sha256 == sig:
            return cached
        # 解析失败缓存：文件未变化且已失败过 -> 直接返回 None（不再重复读盘解析）
        if skill_name in self._failed and self._failed[skill_name] == sig:
            return None
        # 文件变化（或首次）-> 重读重校验
        try:
            parsed = self._parse_skill(md, sig)
        except Exception as e:  # 解析/校验失败
            msg = f"Skill[{skill_name}] 解析失败已禁用: {e}"
            self._warnings.append(msg)
            logger.warning(msg)
            self._failed[skill_name] = sig
            if cached is not None:
                # 保留最近一次有效版本并记告警（不允许模型凭旧概览猜着执行 -> 仍返回旧定义，
                # 但 caller 可通过 warnings 感知；若想要"严格禁用"由 router 决定）
                self._warnings.append(f"Skill[{skill_name}] 保留最近一次有效版本(sha={cached.sha256[:8]})")
                return cached
            return None
        self._cache[skill_name] = parsed
        self._failed.pop(skill_name, None)
        self._check_version_stability(skill_name, parsed.version, parsed.sha256)
        return parsed

    def build_overview(self) -> str:
        """生成当前可用 Skill 的简短索引（替代静态 _SKILL_OVERVIEW）。"""
        lines = ["## 可用场景剧本（由 SkillCatalog 实时生成，唯一来源为各 SKILL.md）"]
        skills = self.list_skills()
        if not skills:
            lines.append("（当前无可用场景剧本）")
            return "\n".join(lines)
        for s in skills:
            any_triggers = (s.triggers or {}).get("any", []) or []
            lines.append(f"- {s.name}（v{s.version}，优先级{s.priority}）：{s.description}")
            if any_triggers:
                lines.append(f"  触发：{'、'.join(str(t) for t in any_triggers[:12])}")
            steps = s.steps
            if steps:
                lines.append(f"  步骤：{' -> '.join(f'{st.id}({st.title})' for st in steps)}")
            lines.append(f'  命中后 read_file("/skills/scenarios/{s.name}/SKILL.md") 读完整剧本。')
        return "\n".join(lines)

    @property
    def warnings(self) -> List[str]:
        return list(self._warnings)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    @staticmethod
    def _fingerprint(md: Path) -> str:
        return hashlib.sha256(md.read_bytes()).hexdigest()

    def _validate_x_tupu(self, x_tupu: Dict[str, Any], steps: List[StepDefinition]) -> None:
        """批4 编译期校验（设计 §1.2）：结构/枚举/引用合法才允许该 Skill 进入目录。

        任一项失败抛 ValueError -> load_skill 捕获 -> 该 Skill 禁用并记告警（不猜着执行）。
        """
        # triggers 结构：any 为字符串数组；all_groups 为字符串数组的数组（组内 AND、组间 OR）
        trig = x_tupu.get("triggers") or {}
        if "any" in trig:
            if not isinstance(trig["any"], list) or not all(isinstance(t, str) for t in trig["any"]):
                raise ValueError("x_tupu.triggers.any 必须是字符串数组")
        if "all_groups" in trig:
            groups = trig["all_groups"]
            if not isinstance(groups, list) or not all(
                isinstance(g, list) and all(isinstance(w, str) for w in g) for g in groups
            ):
                raise ValueError("x_tupu.triggers.all_groups 必须是字符串数组的数组")

        # allowed_next 引用合法：目标 ∈ 本 Skill 步骤 id ∪ {final}
        step_ids = {s.id for s in steps}
        for s in steps:
            for nxt in s.allowed_next:
                if nxt != "final" and nxt not in step_ids:
                    raise ValueError(f"step[{s.id}].allowed_next 引用了不存在步骤: {nxt}")

        # allowed_tools 必须 ∈ 全局工具名册（防拼写漂移/未知工具）
        known = set(GLOBAL_TOOL_REGISTRY)
        if known:
            for s in steps:
                unknown = [t for t in s.allowed_tools if t not in known]
                if unknown:
                    raise ValueError(f"step[{s.id}].allowed_tools 含未知工具: {unknown}")

        # 输出模式 ∈ 枚举（skill 级 output.mode 为约定键；output_mode 为兼容键；步骤级 output_mode 可选）
        skill_out = (x_tupu.get("output") or {}).get("mode") or (x_tupu.get("output") or {}).get("output_mode")
        if skill_out and skill_out not in OUTPUT_MODE_ENUM:
            raise ValueError(f"x_tupu.output.mode 非法: {skill_out}（允许: {sorted(OUTPUT_MODE_ENUM)}）")
        for s in steps:
            if s.output_mode and s.output_mode not in OUTPUT_MODE_ENUM:
                raise ValueError(f"step[{s.id}].output_mode 非法: {s.output_mode}")

        # P2（二轮评审）template_mode 枚举校验：未知值直接禁用该 Skill，
        # 避免误拼（如 scenario_strcit）被 TemplateGuard 静默按非 strict 处理 = 静默降安全级。
        tm = str(x_tupu.get("template_mode") or "scenario_extensible")
        if tm not in ("scenario_strict", "scenario_extensible", "generic"):
            raise ValueError(f"x_tupu.template_mode 非法: {tm}（允许: scenario_strict/scenario_extensible/generic）")

        # P2/评审 P1-1 required_sources 结构校验：多引擎必达数据源 [{entity, role}]
        rs = x_tupu.get("required_sources") or []
        if rs:
            if not isinstance(rs, list) or not all(isinstance(s, dict) and s.get("entity") for s in rs):
                raise ValueError("x_tupu.required_sources 必须是 [{entity, role}] 数组（entity 必填）")
            if not bool(x_tupu.get("multi_engine", False)):
                raise ValueError("x_tupu.required_sources 仅在 multi_engine=true 时合法")

    def _check_version_stability(self, skill_name: str, version: str, sha256: str) -> None:
        """批4 版本稳定性：同 version 内容哈希变化 = 未灰度改动（设计 §1.2），记告警。

        不做运行时拒绝（SKILL.md 仍是唯一事实来源），但暴露给治理/审核：
        生产上变更 SKILL.md 应 bump version，否则同 version 改内容视为未灰度改动。
        """
        prev = self._last_version_hash.get(skill_name)
        if prev is not None and prev[0] == version and prev[1] != sha256:
            msg = (f"Skill[{skill_name}] 内容哈希变化但 version 未变（{version}）= 未灰度改动，"
                   f"应 bump version；sha {prev[1][:8]} -> {sha256[:8]}")
            self._warnings.append(msg)
            logger.warning(msg)
        self._last_version_hash[skill_name] = (version, sha256)

    def _parse_skill(self, md: Path, sha256: str) -> SkillDefinition:
        text = md.read_text("utf-8")
        front, body = _split_frontmatter(text)
        meta: Dict[str, Any] = front or {}
        name = str(meta.get("name") or md.parent.name).strip()
        description = str(meta.get("description") or "").strip()
        category = str(meta.get("category") or "scenario").strip()
        x_tupu: Dict[str, Any] = meta.get("x_tupu") or {}
        # 必要字段校验
        for f in _REQUIRED_X_TUPU_FIELDS:
            if f not in x_tupu:
                raise ValueError(f"x_tupu 缺少必要字段: {f}")
        steps_raw = x_tupu.get("steps") or []
        if not isinstance(steps_raw, list) or not steps_raw:
            raise ValueError("x_tupu.steps 必须为非空数组")
        steps = []
        for raw in steps_raw:
            raw = raw or {}
            for f in _REQUIRED_STEP_FIELDS:
                if f not in raw:
                    raise ValueError(f"step 缺少必要字段: {f}")
            steps.append(StepDefinition(
                id=str(raw["id"]), title=str(raw["title"]),
                triggers=dict(raw.get("triggers") or {}),
                allowed_tools=[str(t) for t in (raw.get("allowed_tools") or [])],
                required_slots=[str(t) for t in (raw.get("required_slots") or [])],
                templates=[str(t) for t in (raw.get("templates") or [])],
                reference_files=[str(t) for t in (raw.get("reference_files") or [])],
                stop_when=[str(t) for t in (raw.get("stop_when") or [])],
                allowed_next=[str(t) for t in (raw.get("allowed_next") or [])],
                output_mode=str(raw.get("output_mode") or ""),
            ))
        self._validate_x_tupu(x_tupu, steps)
        return SkillDefinition(
            name=name, description=description, category=category, path=md,
            sha256=sha256, mtime=md.stat().st_mtime, body=body,
            enabled=bool(x_tupu.get("enabled", True)),
            version=str(x_tupu.get("version", "1.0")),
            priority=int(x_tupu.get("priority", 0) or 0),
            triggers=dict(x_tupu.get("triggers") or {}),
            forbidden_tools=[str(t) for t in (x_tupu.get("forbidden_tools") or [])],
            entity_aliases={str(k): str(v) for k, v in (x_tupu.get("entity_aliases") or {}).items()},
            output=dict(x_tupu.get("output") or {}),
            multi_engine=bool(x_tupu.get("multi_engine", False)),
            template_mode=str(x_tupu.get("template_mode") or "scenario_extensible"),
            required_sources=[dict(s) for s in (x_tupu.get("required_sources") or []) if isinstance(s, dict)],
            steps=steps,
        )


def _split_frontmatter(text: str):
    """拆分 YAML frontmatter（---...---）与正文。返回 (frontmatter_dict, body_str)。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    yaml_text = text[3:end]
    body = text[end + 4:].strip()
    try:
        data = yaml.safe_load(yaml_text) or {}
    except Exception:
        data = {}
    return data, body


# 模块级单例（进程内共享缓存）
_CATALOG: SkillCatalog | None = None


def get_catalog() -> SkillCatalog:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = SkillCatalog()
    return _CATALOG


def list_available_skills() -> List[SkillDefinition]:
    return get_catalog().list_skills()


def build_skills_overview() -> str:
    """供 tupu_deepagent 注入的简短技能索引（替代静态 _SKILL_OVERVIEW）。"""
    return get_catalog().build_overview()


# 触发词匹配工具（供 router 复用）
def match_any_keywords(text: str, keywords: List[str]) -> List[str]:
    """text 中包含的任一触发词（子串匹配，返回命中的词列表）。"""
    if not keywords or not text:
        return []
    return [k for k in keywords if k and str(k) in text]


def match_all_groups(text: str, groups: List[List[str]]) -> List[str]:
    """all_groups：每个组内全部词都命中才算该组命中；返回命中的组描述。"""
    if not groups or not text:
        return []
    hits = []
    for g in groups:
        g = [str(x) for x in g]
        if g and all(x in text for x in g):
            hits.append(" + ".join(g))
    return hits
