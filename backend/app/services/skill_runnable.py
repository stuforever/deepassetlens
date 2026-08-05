"""
SkillRunnable: 把技能五件套包装成 langchain Runnable + langgraph 节点

架构:
  langgraph 节点 (skill_node)
    └─ SkillRunnable (langchain Runnable 接口)
         └─ SkillManager.execute() (技能生命周期管理)
              ├─ SandboxExecutor (v2_skills 沙箱, 受限)
              └─ DirectLoader (问数技能, 完整 Python + importlib)

使用方式:
  # 1. 作为 langgraph 节点
  g.add_node("定位L2", skill_node("locate_l2"))

  # 2. 作为 langchain Runnable
  runnable = SkillRunnable("locate_l2", injections={...})
  result = runnable.invoke({"user_query": "查用电客户"})
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from langchain_core.runnables import Runnable, RunnableConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 技能模块缓存 + 加载器
# ---------------------------------------------------------------------------

_MODULE_CACHE: Dict[str, Any] = {}  # skill_code -> module


def _get_skill_script_path(skill_code: str) -> Path:
    """获取技能脚本路径"""
    return (
        Path(__file__).resolve().parent.parent.parent
        / "data" / "skills" / skill_code / "scripts" / "main.py"
    )


def load_skill_module(skill_code: str, force_reload: bool = False):
    """
    加载技能模块（importlib，完整 Python 能力）。
    与问数流程的 _get_new_skill_module 逻辑一致，但独立维护。

    支持两种来源:
      1. data/skills/{skill_code}/scripts/main.py (文件系统)
      2. SkillManager 存储的脚本 (v2_skills 保存的)
    """
    if skill_code in _MODULE_CACHE and not force_reload:
        return _MODULE_CACHE[skill_code]

    script = _get_skill_script_path(skill_code)
    if not script.exists():
        raise FileNotFoundError(f"技能脚本不存在: {script}")

    mod_name = f"skill_runnable_{skill_code}"
    spec = importlib.util.spec_from_file_location(mod_name, script)
    if not spec or not spec.loader:
        raise RuntimeError(f"无法加载技能 {skill_code}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)

    _MODULE_CACHE[skill_code] = mod
    return mod


def inject_dependencies(mod, skill_code: str, injections: Dict[str, Any]):
    """
    向技能模块注入依赖（沙箱注入）。
    注入的属性名与问数流程的 _inject_new_skill_globals 保持兼容。
    """
    for key, value in injections.items():
        attr_name = f"_injected_{key}" if not key.startswith("_injected_") else key
        setattr(mod, attr_name, value)


def auto_structured_output(chat, schema):
    """自动选择结构化输出策略：先试 function_calling，失败再试 json_schema。

    不同模型支持的能力不同：
    - GLM-5.2: 支持 function_calling，不支持 json_schema
    - DeepSeek-V4-Pro: 支持 json_schema，不支持 function_calling

    用法:
        structured = auto_structured_output(chat, MyPydanticModel)
        result = structured.invoke([SystemMessage(...), HumanMessage(...)])
    """
    for method in ["function_calling", "json_schema"]:
        try:
            return chat.with_structured_output(schema, method=method)
        except Exception:
            continue
    # fallback: 不指定 method
    return chat.with_structured_output(schema)


def inject_stream_writer(mod, writer):
    """单独注入 StreamWriter（兼容技能脚本的 _injected_stream_writer 用法）"""
    if writer is not None:
        mod._injected_stream_writer = writer


# ---------------------------------------------------------------------------
# SkillRunnable: langchain Runnable 适配器
# ---------------------------------------------------------------------------


class SkillRunnable(Runnable):
    """
    把技能五件套包装成 langchain Runnable。

    技能五件套:
      1. input_schema  -> Runnable 输入校验（从 skills 表加载）
      2. output_schema -> Runnable 输出校验（从 skills 表加载）
      3. script        -> invoke() 内部执行（data/skills/ 目录）
      4. injections    -> __init__ 参数（LLM/向量/数据库等）
      5. skill_type    -> 加载方式选择（python/sql/http）
    """

    def __init__(
        self,
        skill_code: str,
        injections: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[Dict], None]] = None,
        stream_writer: Optional[Any] = None,
    ):
        self.skill_code = skill_code
        self.injections = injections or {}
        self.on_progress = on_progress
        self.stream_writer = stream_writer
        self._module = None
        # 从数据库加载元数据（input_schema / output_schema）
        self._input_schema = None
        self._output_schema = None
        self._load_metadata()

    def _load_metadata(self):
        """从 skills + skill_versions 表加载 input_schema / output_schema"""
        try:
            from app.core.database import SessionLocal
            from app.models.skill import Skill, SkillVersion
            db = SessionLocal()
            try:
                skill = db.query(Skill).filter(Skill.skill_code == self.skill_code).first()
                if skill and skill.current_version_id:
                    version = db.query(SkillVersion).filter(
                        SkillVersion.version_id == skill.current_version_id
                    ).first()
                    if version:
                        self._input_schema = version.input_schema
                        self._output_schema = version.output_schema
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"SkillRunnable[{self.skill_code}] 加载元数据失败: {e}")

    def _validate_input(self, input_data: Dict[str, Any]):
        """按 input_schema 校验必填字段"""
        if not self._input_schema:
            return
        required = self._input_schema.get("required", [])
        missing = [f for f in required if f not in input_data]
        if missing:
            raise ValueError(f"技能 {self.skill_code} 缺少必填字段: {missing}")

    def _validate_output(self, result: Dict[str, Any]):
        """按 output_schema 校验返回值"""
        if not self._output_schema:
            return
        required = self._output_schema.get("required", [])
        missing = [f for f in required if f not in result]
        if missing:
            logger.warning(f"技能 {self.skill_code} 返回值缺少字段: {missing}")

    def _ensure_module(self):
        """延迟加载技能模块（首次 invoke 时加载）"""
        if self._module is None:
            self._module = load_skill_module(self.skill_code)
            inject_dependencies(self._module, self.skill_code, self.injections)
            # 注入 on_progress 回调
            if self.on_progress:
                self._module._injected_on_progress = self.on_progress
            # 注入 stream_writer（兼容技能脚本的 _injected_stream_writer）
            if self.stream_writer:
                inject_stream_writer(self._module, self.stream_writer)
        else:
            # 每次重新注入（LLM 客户端可能失效）
            inject_dependencies(self._module, self.skill_code, self.injections)
            if self.on_progress:
                self._module._injected_on_progress = self.on_progress
            if self.stream_writer:
                inject_stream_writer(self._module, self.stream_writer)

    def invoke(
        self,
        input: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        标准 Runnable.invoke 接口。

        1. 校验输入（input_schema）
        2. 加载技能模块
        3. 注入依赖
        4. 调用 mod.execute(input)
        5. 校验输出（output_schema）
        6. 返回结果（dict）
        """
        # 1. 输入校验
        self._validate_input(input)

        self._ensure_module()

        try:
            result = self._module.execute(input)
            if not isinstance(result, dict):
                result = {"status": "error", "error": f"技能返回非 dict: {type(result)}"}
            # 5. 输出校验（只警告，不阻断）
            self._validate_output(result)
            return result
        except Exception as e:
            logger.exception(f"SkillRunnable[{self.skill_code}] 执行失败")
            return {"status": "error", "error": str(e)}

    async def ainvoke(
        self,
        input: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """异步接口（暂走同步，后续可改为 asyncio.to_thread）"""
        return self.invoke(input, config, **kwargs)

    async def invoke_astream(
        self,
        input: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """异步流式接口：优先调技能模块的 execute_astream（逐 token 推理）。
        若技能未实现 execute_astream，回退到同步 execute。
        流式推理 token 通过 langgraph 的 get_stream_writer() 推送（由技能脚本内部调用），
        因此本方法在 DeepAgent 的 async @tool 内调用时，writer 由 graph 上下文注入。"""
        self._validate_input(input)
        self._ensure_module()
        try:
            fn = getattr(self._module, "execute_astream", None)
            if fn is None:
                # 技能未实现 async 入口，回退同步（无流式推理）
                return self._module.execute(input)
            result = await fn(input)
            if not isinstance(result, dict):
                result = {"status": "error", "error": f"技能返回非 dict: {type(result)}"}
            self._validate_output(result)
            return result
        except Exception as e:
            logger.exception(f"SkillRunnable[{self.skill_code}] 流式执行失败")
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# skill_node: langgraph 节点工厂函数
# ---------------------------------------------------------------------------


def skill_node(
    skill_code: str,
    injections: Optional[Dict[str, Any]] = None,
    extract_input: Optional[Callable] = None,
    apply_result: Optional[Callable] = None,
):
    """
    把技能包装成 langgraph 节点函数。

    参数:
      skill_code: 技能编码（对应 data/skills/{skill_code}/）
      injections: 依赖注入字典（LLM/向量/数据库等）
      extract_input: 从 GraphState 提取技能输入的函数
                     签名: (sec: SecretaryState) -> dict
      apply_result: 把技能结果写回 GraphState 的函数
                    签名: (sec: SecretaryState, result: dict) -> None

    返回:
      langgraph 节点函数 (state, writer) -> state

    使用:
      g.add_node("定位L2", skill_node("locate_l2",
          injections={"llm_chat_model": build_llm_chat_model()},
          extract_input=lambda sec: {"user_query": sec.user_input},
          apply_result=lambda sec, r: setattr(sec.confirmed, 'L2', r.get('l2_name','')),
      ))
    """
    from app.services.secretary_state import (
        secretary_state_to_dict,
        SecretaryState,
    )

    # 默认注入：每次构建节点时刷新
    _injections = injections or {}

    def node_fn(state: Dict[str, Any], writer=None) -> Dict[str, Any]:
        # 1. 恢复秘书态
        sec_data = state.get("secretary_state") or {}
        sec = SecretaryState(**sec_data) if isinstance(sec_data, dict) else sec_data

        # 2. 提取输入
        if extract_input:
            input_data = extract_input(sec)
        else:
            input_data = {"user_query": sec.user_input or sec.original_query or ""}

        # 3. 构建 on_progress 回调（推送 think 事件到 langgraph StreamWriter）
        def _on_progress(event: Dict):
            if writer and isinstance(event, dict):
                writer(event)

        # 4. 合并注入（默认 + 运行时）
        runtime_injections = {**_injections}

        # 5. 创建 Runnable 并执行
        runnable = SkillRunnable(
            skill_code=skill_code,
            injections=runtime_injections,
            on_progress=_on_progress,
        )
        result = runnable.invoke(input_data)

        # 6. 写回 state
        if apply_result:
            apply_result(sec, result)
        else:
            # 默认写回逻辑：把 result 合并到 state
            state["last_skill_result"] = result

        # 7. 推送 think 事件
        if writer and result.get("status"):
            think_item = {
                "task": skill_code,
                "strategy": result.get("strategy", ""),
                "action": result.get("action", ""),
                "reason": result.get("reason", ""),
                "process": result.get("process"),
                "result_status": result.get("status"),
            }
            writer({"type": "think", **think_item})

        # 8. 写回 secretary_state
        state["secretary_state"] = secretary_state_to_dict(sec)
        state["trace"] = state.get("trace", []) + [
            {"node": skill_code, "status": result.get("status", "unknown")}
        ]

        return state

    return node_fn


# ---------------------------------------------------------------------------
# 辅助：构建标准注入字典
# ---------------------------------------------------------------------------


def build_default_injections(skill_code: str) -> Dict[str, Any]:
    """
    按技能编码构建默认注入字典。
    与 data_intelligence_graph.py 的 _inject_new_skill_globals 逻辑对齐。
    """
    from app.services.skill_injections import (
        build_llm_client,
        build_llm_chat_model,
        build_vector_recall_fn,
        build_attribute_vector_search_fn,
        build_fetch_l1_l2_tree,
        build_fetch_subgraph_by_l2,
        build_fetch_entity_attributes,
        build_search_knowledge,
    )

    injections = {}

    # 通用：LLM 客户端（两种都注入，技能自选）
    try:
        injections["llm_client"] = build_llm_client()
    except Exception:
        pass
    try:
        injections["llm_chat_model"] = build_llm_chat_model()
    except Exception:
        pass

    # locate_entity_attribute + explore：向量召回
    if skill_code in ("locate_entity_attribute", "locate_entity_attr", "explore"):
        try:
            injections["entity_vector_recall"] = build_vector_recall_fn()
        except Exception:
            pass
        try:
            injections["attribute_vector_search"] = build_attribute_vector_search_fn()
        except Exception:
            pass

    # locate_l2：L1-L2 层级树
    if skill_code == "locate_l2":
        try:
            injections["fetch_l1_l2_tree"] = build_fetch_l1_l2_tree()
        except Exception:
            pass

    # locate_entity_attr：L2 子图
    if skill_code == "locate_entity_attr":
        try:
            injections["fetch_subgraph_by_l2"] = build_fetch_subgraph_by_l2()
        except Exception:
            pass

    # sql_assembly：SQL 执行 + 动态 JOIN 关系查询
    if skill_code == "sql_assembly":
        # _build_execute_query_fn 在 sql_executor 里定义
        # 这里延迟导入避免循环
        try:
            from app.services.sql_executor import _build_execute_query_fn
            injections["execute_query"] = _build_execute_query_fn()
        except Exception:
            pass
        # 动态 JOIN 关系查询（从 kg_entity_relations 表查真实关联字段）
        try:
            injections["fetch_join_expr"] = _build_fetch_join_expr_fn()
        except Exception:
            pass

    # knowledge_qa：知识检索
    if skill_code == "knowledge_qa":
        try:
            injections["search_knowledge"] = build_search_knowledge()
        except Exception:
            pass

    return injections


# ---------------------------------------------------------------------------
# 动态 JOIN 关系查询
# ---------------------------------------------------------------------------


def _build_fetch_join_expr_fn():
    """
    构造 JOIN 关系查询函数。
    从 kg_entity_relations 表查两个实体之间的真实关联字段。

    返回函数签名: (source_entity_code: str, target_entity_code: str) -> str | None
    返回值: "table1.field1 = table2.field2" 或 None（没找到则 fallback 到 cust_id）
    """
    def _fetch_join_expr(source_code: str, target_code: str):
        try:
            from app.core.database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            try:
                # 双向查（source->target 或 target->source）
                result = db.execute(text("""
                    SELECT er.source_field_name, er.target_field_name, er.join_expr,
                           e1.entity_code as src_code, e2.entity_code as tgt_code
                    FROM kg_entity_relations er
                    JOIN kg_entities e1 ON er.source_entity_id = e1.id
                    JOIN kg_entities e2 ON er.target_entity_id = e2.id
                    WHERE (e1.entity_code = :src AND e2.entity_code = :tgt)
                       OR (e1.entity_code = :tgt AND e2.entity_code = :src)
                    LIMIT 1
                """), {"src": source_code, "tgt": target_code})
                row = result.fetchone()
                if not row:
                    return None

                src_field = row[0]  # source_field_name
                tgt_field = row[1]  # target_field_name
                join_expr = row[2]  # join_expr (可能是 "cust_no = cust_no")

                # 确定 source_code 和 target_code 的方向
                actual_src = row[3]  # src_code
                actual_tgt = row[4]  # tgt_code

                # 如果数据库里的方向和请求相反，交换字段
                if actual_src == target_code and actual_tgt == source_code:
                    src_field, tgt_field = tgt_field, src_field

                # 优先用 join_expr（但需要加上表名前缀）
                if join_expr and "=" in join_expr:
                    # join_expr 格式: "cust_no = cust_no"
                    parts = [p.strip() for p in join_expr.split("=")]
                    if len(parts) == 2:
                        return f"{source_code}.{parts[0]} = {target_code}.{parts[1]}"

                # 用 source_field_name / target_field_name
                if src_field and tgt_field:
                    return f"{source_code}.{src_field} = {target_code}.{tgt_field}"

                return None
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"fetch_join_expr 查询失败: {e}")
            return None

    return _fetch_join_expr


# ---------------------------------------------------------------------------
# P3: 通用路由函数工厂
# ---------------------------------------------------------------------------


def skill_router(
    next_on_locked: str = None,
    next_on_clarify: str = "clarify",
    next_on_other: str = "next_step",
):
    """
    通用技能路由函数工厂。
    根据技能返回的 status 和秘书态的 pending_clarification 决定下一个节点。

    参数:
      next_on_locked: status=locked 时去哪个节点（None 表示用自动链逻辑）
      next_on_clarify: 有澄清时去哪个节点（默认 "clarify"）
      next_on_other: 其他情况去哪个节点（默认 "next_step"）

    使用:
      g.add_conditional_edges("定位L2", skill_router(next_on_locked="定位实体属性"), {...})
    """
    def router(state: Dict[str, Any]) -> str:
        sec_data = state.get("secretary_state") or {}
        # 简单检查 pending_clarification
        pending = sec_data.get("pending_clarification") if isinstance(sec_data, dict) else None
        if not pending:
            # 也检查 state 顶层
            pending = state.get("pending_clarification")
        if pending:
            return next_on_clarify

        # 检查锁定状态
        if next_on_locked:
            # 自动链逻辑：实体+属性都锁 -> next_on_locked
            chain_locked = sec_data.get("chain_locked", False) if isinstance(sec_data, dict) else False
            entity_locked = sec_data.get("entity_locked", False) if isinstance(sec_data, dict) else False
            attribute_locked = sec_data.get("attribute_locked", False) if isinstance(sec_data, dict) else False

            if next_on_locked == "定位实体属性" and chain_locked:
                return next_on_locked
            if next_on_locked == "SQL拼装" and entity_locked and attribute_locked:
                return next_on_locked

        return next_on_other

    return router
