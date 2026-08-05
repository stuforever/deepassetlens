"""
技能执行引擎 (v2)
五件套文件系统存储：运行时从文件系统读取脚本执行
"""

import json
import re
import uuid
import traceback
import sys
import types
import concurrent.futures
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.skill import Skill, SkillVersion, SkillExecLog
from app.services.skill_manager import SkillService, VersionService, ExecutionService
from app.core.dag_parser import DAGParser
from app.core.jsonschema_validator import validate_input
from app.core.skill_storage import get_skill_storage, SkillStorage

logger = logging.getLogger(__name__)


class SandboxExecutor:
    """
    Python 沙箱执行器
    限制 builtins，只允许安全操作
    5.3 依赖预热：编译结果缓存，二次执行命中缓存
    """

    _compile_cache: Dict[str, Any] = {}

    ALLOWED_BUILTIN_NAMES = {
        'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'chr', 'dict', 'dir',
        'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
        'getattr', 'hasattr', 'hash', 'hex', 'id', 'int', 'isinstance',
        'issubclass', 'iter', 'len', 'list', 'map', 'max', 'min', 'next',
        'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed', 'round',
        'set', 'setattr', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type',
        'vars', 'zip',
        'Exception', 'ValueError', 'TypeError', 'KeyError',
        'IndexError', 'AttributeError', 'RuntimeError', 'StopIteration',
        'NotImplementedError', 'OverflowError', 'ZeroDivisionError',
        'NameError', 'PermissionError', 'ImportError', 'ModuleNotFoundError',
        '__import__', '__build_class__', '__name__',
    }

    @staticmethod
    def _build_safe_builtins(permissions: dict = None) -> dict:
        import builtins as _builtins_mod
        perms = permissions or {}
        allowed = set(SandboxExecutor.ALLOWED_BUILTIN_NAMES)

        if not perms.get('network', True):
            for name in ['open', '__import__']:
                allowed.discard(name)
        if not perms.get('filesystem', False):
            for name in ['open', 'file']:
                allowed.discard(name)

        safe_bi = {'__builtins__': True}
        for name in allowed:
            obj = getattr(_builtins_mod, name, None)
            if obj is not None:
                safe_bi[name] = obj
        return safe_bi

    @staticmethod
    def create_safe_globals(permissions: dict = None) -> dict:
        perms = permissions or {}
        safe_globals = {
            '__builtins__': SandboxExecutor._build_safe_builtins(perms),
        }
        safe_globals['json'] = json
        safe_globals['re'] = re
        safe_globals['datetime'] = datetime
        safe_globals['traceback'] = traceback
        safe_globals['__permissions__'] = perms
        return safe_globals

    @staticmethod
    def execute(script: str, entrypoint: str, inputs: dict,
                timeout: int = 30, resource_limits: dict = None,
                permissions: dict = None, inject_globals: dict = None) -> dict:
        """
        在安全沙箱中执行 Python 脚本
        """
        import io
        import time as _time

        perms = permissions or {}
        safe_globals = SandboxExecutor.create_safe_globals(perms)
        if inject_globals:
            safe_globals.update(inject_globals)
            logger.debug(f"SandboxExecutor: 注入的全局变量: {list(inject_globals.keys())}")
        logs: list = []
        start_ts = _time.time()

        def _sandbox_print(*args, **kwargs):
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            line = sep.join(str(a) for a in args) + end
            logs.append({"level": "INFO", "message": line.rstrip(), "time": datetime.utcnow().isoformat()})

        safe_globals['__builtins__']['print'] = _sandbox_print

        try:
            if not perms.get('filesystem', False):
                def _forbidden_open(*args, **kwargs):
                    raise PermissionError("文件系统访问被禁止（permissions.filesystem=false）")
                safe_globals['__builtins__']['open'] = _forbidden_open

            logs.append({"level": "SYSTEM", "message": f"开始执行脚本，入口: {entrypoint}", "time": datetime.utcnow().isoformat()})

            import hashlib
            cache_key = hashlib.md5(script.encode()).hexdigest()
            if cache_key in SandboxExecutor._compile_cache:
                compiled = SandboxExecutor._compile_cache[cache_key]
                logs.append({"level": "SYSTEM", "message": "命中编译缓存，跳过 compile", "time": datetime.utcnow().isoformat()})
            else:
                compiled = compile(script, '<skill_script>', 'exec')
                SandboxExecutor._compile_cache[cache_key] = compiled
                logs.append({"level": "SYSTEM", "message": "脚本编译完成", "time": datetime.utcnow().isoformat()})

            exec(compiled, safe_globals)
            logs.append({"level": "SYSTEM", "message": "脚本加载完成，查找入口函数", "time": datetime.utcnow().isoformat()})

            if entrypoint not in safe_globals:
                raise ValueError(f"入口函数 '{entrypoint}' 不存在于脚本中")

            func = safe_globals[entrypoint]
            if not callable(func):
                raise ValueError(f"'{entrypoint}' 不是可调用函数")

            logs.append({"level": "SYSTEM", "message": f"调用 {entrypoint}()，输入: {json.dumps(inputs, ensure_ascii=False, default=str)[:200]}", "time": datetime.utcnow().isoformat()})
            result = func(inputs)
            elapsed = int((_time.time() - start_ts) * 1000)
            logs.append({"level": "SYSTEM", "message": f"执行完成，耗时 {elapsed}ms", "time": datetime.utcnow().isoformat()})

            if not isinstance(result, dict):
                raise ValueError(f"入口函数必须返回 dict，实际返回 {type(result).__name__}")

            return {
                "success": True,
                "output": result,
                "logs": logs
            }

        except PermissionError as e:
            logs.append({"level": "ERROR", "message": f"权限错误: {e}", "time": datetime.utcnow().isoformat()})
            return {
                "success": False,
                "error": str(e),
                "type": "permission_denied",
                "logs": logs
            }
        except Exception as e:
            logs.append({"level": "ERROR", "message": f"执行异常: {e}", "time": datetime.utcnow().isoformat()})
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "logs": logs
            }


class TemplateRenderer:
    """
    模板渲染器
    支持 {{variable}} 语法
    """

    @staticmethod
    def render(template: str, context: dict) -> str:
        """渲染模板字符串"""
        def replace_var(match):
            var_path = match.group(1).strip()
            return TemplateRenderer._get_nested_value(context, var_path, match.group(0))

        return re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var, template)

    @staticmethod
    def render_dict(data: dict, context: dict) -> dict:
        """递归渲染字典中的模板"""
        if isinstance(data, str):
            return TemplateRenderer.render(data, context)
        elif isinstance(data, dict):
            return {k: TemplateRenderer.render_dict(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [TemplateRenderer.render_dict(item, context) for item in data]
        return data

    @staticmethod
    def _get_nested_value(data: dict, path: str, default: Any = None) -> Any:
        """获取嵌套字典值"""
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current


class SkillExecutor:
    """
    技能执行器基类
    """

    def __init__(self, db: Session):
        self.db = db

    def execute(self, skill: Skill, version: SkillVersion,
                input_payload: dict, execution_code: str) -> dict:
        raise NotImplementedError


class PythonExecutor(SkillExecutor):
    """Python 技能执行器 - 从文件系统读取脚本"""

    def execute(self, skill: Skill, version: SkillVersion,
                input_payload: dict, execution_code: str) -> dict:
        # 从文件系统读取入口脚本
        storage = get_skill_storage()
        try:
            script = storage.get_entrypoint_script(skill.skill_code, "python")
        except FileNotFoundError:
            return {"success": False, "error": "找不到入口脚本 scripts/main.py"}

        entrypoint = "execute"  # 固定入口

        # 加载常用语气词并注入到脚本全局变量
        inject_globals = {}
        inject_globals["_db_session"] = self.db
        try:
            from app.models.base import CommonStopWord
            rows = self.db.query(CommonStopWord).filter(CommonStopWord.enabled == True).all()
            stop_words = [w.word for w in rows]
            inject_globals['_common_stop_words'] = stop_words
            logger.debug(f"PythonExecutor: 注入 {len(stop_words)} 个常用语气词到 _common_stop_words")
        except Exception as e:
            logger.warning(f"PythonExecutor: 加载常用语气词失败: {e}")
            pass

        try:
            from app.models.base import StandardDict
            dict_rows = self.db.query(StandardDict).filter(StandardDict.enabled == True).all()
            standard_dict = [{"non_standard": r.non_standard, "standard": r.standard} for r in dict_rows]
            inject_globals['_standard_dict'] = standard_dict
            logger.debug(f"PythonExecutor: 注入 {len(standard_dict)} 个标准词典项到 _standard_dict")
        except Exception as e:
            logger.warning(f"PythonExecutor: 加载标准词典失败: {e}")
            pass

        # NL2Cypher 语义数据注入（18个动作子技能 + pipeline）
        nl2cypher_skills = {"nl2cypher", "nl2cypher_pipeline",
            "step1_1_remove_stop_words", "step1_2_extract_time", "step1_3_extract_intent", "step1_4_explode_metric", "step1_5_ac_replace",
            "step2_1_classify_words", "step2_2_vector_search", "step2_3_validate_belonging",
            "step3_1_route_intent", "step3_2_check_clarify", "step3_3_llm_assemble",
            "step4_1_fill_template", "step4_2_validate_cypher", "step4_3_llm_fallback_cypher",
            "step5_1_check_complexity", "step5_2_execute_graph",
            "step6_1_final_validate", "step6_2_pack_response"}
        if skill.skill_code in nl2cypher_skills:
            try:
                from app.core.nl2cypher_data_loader import load_semantic_data
                semantic_data = load_semantic_data(self.db)
                inject_globals['_nl2cypher_semantic_data'] = semantic_data
                logger.debug(f"PythonExecutor: 注入 NL2Cypher 语义数据到 {skill.skill_code}")
            except Exception as e:
                logger.warning(f"PythonExecutor: 加载NL2Cypher语义数据失败: {e}")
                pass

        result = SandboxExecutor.execute(
            script=script,
            entrypoint=entrypoint,
            inputs=input_payload,
            timeout=skill.timeout,
            permissions=skill.permissions or {},
            inject_globals=inject_globals
        )

        return result


class SQLExecutor(SkillExecutor):
    """SQL 技能执行器 - 从文件系统读取 SQL"""

    def execute(self, skill: Skill, version: SkillVersion,
                input_payload: dict, execution_code: str) -> dict:
        # 从文件系统读取 SQL
        storage = get_skill_storage()
        try:
            sql = storage.read_file(skill.skill_code, "scripts/main.sql")
        except FileNotFoundError:
            return {"success": False, "error": "找不到 SQL 脚本 scripts/main.sql"}

        database = "default"

        # 渲染 SQL 模板
        rendered_sql = TemplateRenderer.render(sql, input_payload)

        try:
            # 使用当前数据库连接执行（简化实现）
            from sqlalchemy import text
            result_proxy = self.db.execute(text(rendered_sql))

            # 获取结果
            if result_proxy.returns_rows:
                rows = [dict(row._mapping) for row in result_proxy.fetchall()]
                return {
                    "success": True,
                    "output": {
                        "rows": rows,
                        "row_count": len(rows)
                    }
                }
            else:
                return {
                    "success": True,
                    "output": {
                        "message": "执行成功",
                        "row_count": result_proxy.rowcount
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"SQL 执行错误: {str(e)}"
            }


class HTTPExecutor(SkillExecutor):
    """HTTP 技能执行器 - 从文件系统读取配置"""

    def execute(self, skill: Skill, version: SkillVersion,
                input_payload: dict, execution_code: str) -> dict:
        # 检查网络权限
        perms = skill.permissions or {}
        if not perms.get('network', True):
            return {
                "success": False,
                "error": "网络访问被禁止（permissions.network=false）",
                "type": "permission_denied"
            }

        # 从文件系统读取 HTTP 配置
        storage = get_skill_storage()
        try:
            cfg = json.loads(storage.read_file(skill.skill_code, "scripts/main.yaml"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"success": False, "error": f"读取 HTTP 配置失败: {e}"}

        method = cfg.get("method", "GET")
        url = cfg.get("url", "")
        headers = cfg.get("headers", {})
        body_template = cfg.get("body_template")
        auth = cfg.get("auth", {})

        if not url:
            return {"success": False, "error": "URL 为空"}

        # 构建请求上下文
        context = {
            **input_payload,
            "env": self._get_env_vars(auth)
        }

        # 渲染 URL 和 headers
        rendered_url = TemplateRenderer.render(url, context)
        rendered_headers = TemplateRenderer.render_dict(headers, context)

        # 处理认证
        auth_config = self._process_auth(auth, context)
        if auth_config:
            rendered_headers.update(auth_config.get("headers", {}))

        # 渲染 body
        body = None
        if body_template:
            body = TemplateRenderer.render(body_template, context)

        try:
            import urllib.request
            import urllib.parse

            req = urllib.request.Request(
                url=rendered_url,
                data=body.encode('utf-8') if body else None,
                headers=rendered_headers,
                method=method
            )

            with urllib.request.urlopen(req, timeout=skill.timeout) as response:
                response_body = response.read().decode('utf-8')
                try:
                    response_data = json.loads(response_body)
                except json.JSONDecodeError:
                    response_data = {"raw": response_body}

                return {
                    "success": True,
                    "output": {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": response_data
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"HTTP 请求失败: {str(e)}"
            }

    def _get_env_vars(self, auth: dict) -> dict:
        """获取环境变量（用于auth配置）"""
        # 从 permissions.allowed_env 中获取允许的环境变量
        return {}

    def _process_auth(self, auth: dict, context: dict) -> Optional[dict]:
        """处理认证配置"""
        auth_type = auth.get("type", "none")

        if auth_type == "bearer":
            token_ref = auth.get("token_ref", "")
            token = TemplateRenderer.render(token_ref, context)
            return {"headers": {"Authorization": f"Bearer {token}"}}

        elif auth_type == "basic":
            username = auth.get("username", "")
            password = auth.get("password", "")
            import base64
            creds = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"headers": {"Authorization": f"Basic {creds}"}}

        return None


class NaturalExecutor(SkillExecutor):
    """自然语言技能执行器 - 从文件系统读取 prompt"""

    def execute(self, skill: Skill, version: SkillVersion,
                input_payload: dict, execution_code: str) -> dict:
        storage = get_skill_storage()
        try:
            prompt_template = storage.read_file(skill.skill_code, "scripts/main.txt")
        except FileNotFoundError:
            return {"success": False, "error": "找不到 prompt 文件 scripts/main.txt"}

        if not prompt_template:
            return {"success": False, "error": "Prompt 模板为空"}

        rendered_prompt = TemplateRenderer.render(prompt_template, input_payload)

        return {
            "success": True,
            "output": {
                "prompt": rendered_prompt,
                "skill_code": skill.skill_code,
                "skill_name": skill.name
            }
        }


class MixedExecutor(SkillExecutor):
    """混合技能执行器 - 从文件系统读取步骤配置"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.execution_cache = {}
        self.engine = None

    def set_engine(self, engine):
        self.engine = engine

    def execute(self, skill: Skill, version: SkillVersion,
                input_payload: dict, execution_code: str) -> dict:
        import yaml
        storage = get_skill_storage()
        try:
            raw = storage.read_file(skill.skill_code, "scripts/main.yaml")
            cfg = yaml.safe_load(raw)
        except (FileNotFoundError, yaml.YAMLError) as e:
            return {"success": False, "error": f"读取混合技能配置失败: {e}"}

        steps = cfg.get("steps", [])
        active_steps = [step for step in steps if bool((step or {}).get("enabled", True))]

        if not active_steps:
            return {"success": False, "error": "混合技能步骤为空"}

        # 构建DAG定义
        dag_definition = self._build_dag_from_steps(active_steps)

        # 解析DAG
        parser = DAGParser()
        is_valid, error_msg = parser.validate_dag(dag_definition)
        if not is_valid:
            return {"success": False, "error": f"DAG 验证失败: {error_msg}"}

        parsed = parser.parse_dag(dag_definition)

        # 按拓扑顺序执行
        step_results = {}
        step_trace = []

        for node_id in parsed["execution_order"]:
            step = next((s for s in active_steps if s.get("step_id") == node_id), None)
            if not step:
                continue

            # 构建输入（处理 input_mapping）
            step_input = self._resolve_step_input(step, input_payload, step_results)

            # 获取引用的技能
            ref_skill_code = step.get("skill_code")
            if not ref_skill_code:
                return {"success": False, "error": f"步骤 {node_id} 缺少 skill_code"}

            # 执行引用的技能
            if not self.engine:
                return {"success": False, "error": "混合执行器未注入引擎"}

            started_at = time.time()
            result = self.engine.execute_by_code(ref_skill_code, step_input, execution_code)
            duration_ms = int((time.time() - started_at) * 1000)

            if not result.get("success"):
                step_trace.append({
                    "step_id": node_id,
                    "name": step.get("name"),
                    "skill_code": ref_skill_code,
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "input": step_input,
                    "error": result.get("error"),
                })
                return {
                    "success": False,
                    "error": f"步骤 {node_id} 执行失败: {result.get('error')}",
                    "step_results": step_results,
                    "step_trace": step_trace,
                }

            step_output = result.get("output", {}) if isinstance(result, dict) else {}
            if isinstance(step_output, dict) and "output" in step_output and isinstance(step_output.get("output"), dict):
                # 兼容旧技能返回 {"output": {...}} 的嵌套结构
                step_results[node_id] = step_output.get("output") or {}
            else:
                step_results[node_id] = step_output or {}
            step_trace.append({
                "step_id": node_id,
                "name": step.get("name"),
                "skill_code": ref_skill_code,
                "status": "success",
                "duration_ms": duration_ms,
                "input": step_input,
                "output": step_results[node_id],
            })

        # 构建最终输出
        final_output = self._build_final_output(active_steps, step_results)

        return {
            "success": True,
            "output": {
                "final_output": final_output,
                "step_results": step_results,
                "step_trace": step_trace,
            }
        }

    def _build_dag_from_steps(self, steps: list) -> dict:
        """从步骤构建DAG定义"""
        nodes = []
        edges = []
        node_ids = set()

        for step in steps:
            node_id = step.get("step_id")
            nodes.append({"node_id": node_id, "skill_code": step.get("skill_code", "")})
            node_ids.add(node_id)

        # 根据 input_mapping 中的 {{stepX.output}} 构建依赖边
        for step in steps:
            to_id = step.get("step_id")
            input_mapping = step.get("input_mapping", {})

            for mapped_value in input_mapping.values():
                if isinstance(mapped_value, str):
                    # 兼容 {{step_id.output}} 与 {{step_id.output.field}} 两类引用
                    for match in re.finditer(r'\{\{\s*(\w+)\.output(?:\.[\w.]+)?\s*\}\}', mapped_value):
                        from_id = match.group(1)
                        if from_id in node_ids and from_id != to_id and {"from": from_id, "to": to_id} not in edges:
                            edges.append({"from": from_id, "to": to_id})

        return {"nodes": nodes, "edges": edges}

    def _resolve_step_input(self, step: dict, original_input: dict,
                            step_results: dict) -> dict:
        """解析步骤输入（处理 input_mapping）"""
        input_mapping = step.get("input_mapping", {})

        resolved = {}
        for key, value in input_mapping.items():
            if isinstance(value, str):
                # 检查是否是纯引用 {{step_id.output}} 或 {{step_id.output.key}}
                pure_match = re.match(r'^\{\{\s*(\w+)\.output(?:\.([\w.]+))?\s*\}\}$', value.strip())
                if pure_match:
                    ref_step = pure_match.group(1)
                    ref_key = pure_match.group(2)
                    if ref_step in step_results:
                        if ref_key:
                            resolved[key] = self._get_nested_output_value(step_results[ref_step], ref_key)
                        else:
                            resolved[key] = step_results[ref_step]
                    else:
                        resolved[key] = value
                    continue

                # 检查是否是原始输入引用 {{key}}（不含 .output）
                pure_input_match = re.match(r'^\{\{\s*(\w+)\s*\}\}$', value.strip())
                if pure_input_match:
                    input_key = pure_input_match.group(1)
                    if input_key in original_input:
                        resolved[key] = original_input[input_key]
                    continue

                # 字符串中可能有多个引用，做文本替换
                def replace_ref(match):
                    ref_step = match.group(1)
                    ref_key = match.group(2)
                    if ref_step in step_results:
                        if ref_key:
                            return str(self._get_nested_output_value(step_results[ref_step], ref_key, ""))
                        else:
                            return str(step_results[ref_step])
                    return match.group(0)

                resolved_value = re.sub(r'\{\{\s*(\w+)\.output(?:\.([\w.]+))?\s*\}\}', replace_ref, value)
                resolved[key] = resolved_value
            else:
                resolved[key] = value

        # 合并原始输入
        return {**original_input, **resolved}

    def _get_nested_output_value(self, data: Any, path: str, default: Any = None) -> Any:
        current = data
        for key in (path or "").split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _build_final_output(self, steps: list, step_results: dict) -> dict:
        """构建最终输出"""
        # 找到最后一步的输出
        if not steps:
            return {}

        last_step = steps[-1]
        last_step_id = last_step.get("step_id")
        output_mapping = last_step.get("output_mapping", {})

        if output_mapping:
            result = {}
            for out_key, step_ref in output_mapping.items():
                match = re.match(r'\{\{\s*(\w+)\.output\s*\}\}', str(step_ref))
                if match:
                    ref_step = match.group(1)
                    if ref_step in step_results:
                        result[out_key] = step_results[ref_step]
            return result

        return step_results.get(last_step_id, {})


class ExecutionEngineV2:
    """
    技能执行引擎 (v2)
    统一入口，根据 skill_type 分发到不同执行器
    """

    def __init__(self, db: Session):
        self.db = db
        self.executors = {
            "python": PythonExecutor(db),
            "sql": SQLExecutor(db),
            "http": HTTPExecutor(db),
            "natural": NaturalExecutor(db),
            "mixed": MixedExecutor(db)
        }
        # 给 mixed 执行器注入自身引用
        if "mixed" in self.executors:
            self.executors["mixed"].set_engine(self)

    def execute(self, skill_id: uuid.UUID, input_payload: dict,
                version_id: Optional[uuid.UUID] = None,
                created_via: str = "manual") -> dict:
        """
        执行技能（主入口）

        Args:
            skill_id: 技能ID
            input_payload: 输入数据
            version_id: 指定版本ID（默认使用当前激活版本）
            created_via: 创建来源

        Returns:
            dict: 执行结果
        """
        # 获取技能
        skill = SkillService.get_skill(self.db, skill_id)
        if not skill:
            return {"success": False, "error": "技能不存在"}

        # 熔断检查：技能下线时禁止执行
        if skill.status == "archived":
            return {
                "success": False,
                "error": f"技能已下线（status=archived），禁止执行",
                "type": "skill_disabled",
            }

        # 确定版本
        if not version_id:
            version_id = skill.current_version_id

        if not version_id:
            return {"success": False, "error": "技能没有激活的版本"}

        version = VersionService.get_version(self.db, version_id)
        if not version:
            return {"success": False, "error": "版本不存在"}

        # 创建执行记录
        log = ExecutionService.create_execution(
            self.db, skill_id, version_id, input_payload, created_via
        )
        execution_code = log.execution_code

        # 记录开始时间
        start_time = datetime.utcnow()

        try:
            # 校验输入（简单校验）
            validation_result = self._validate_input(version.input_schema, input_payload)
            if not validation_result["valid"]:
                raise ValueError(f"输入校验失败: {validation_result['error']}")

            # 获取执行器
            skill_type = skill.skill_type
            if skill_type not in self.executors:
                raise ValueError(f"不支持的技能类型: {skill_type}")

            executor = self.executors[skill_type]

            # 执行
            result = executor.execute(skill, version, input_payload, execution_code)

            # 计算执行时长
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # 更新执行记录
            if result.get("success"):
                ExecutionService.complete_execution(
                    self.db, execution_code,
                    output_data=result.get("output"),
                    error_message=None,
                    duration_ms=duration_ms
                )
            else:
                ExecutionService.complete_execution(
                    self.db, execution_code,
                    output_data=None,
                    error_message=result.get("error"),
                    duration_ms=duration_ms
                )

            return {
                "success": result.get("success", False),
                "execution_code": execution_code,
                "output": result.get("output"),
                "error": result.get("error"),
                "duration_ms": duration_ms,
                "logs": result.get("logs", [])
            }

        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            ExecutionService.complete_execution(
                self.db, execution_code,
                output_data=None,
                error_message=str(e),
                duration_ms=duration_ms
            )

            return {
                "success": False,
                "execution_code": execution_code,
                "error": str(e),
                "duration_ms": duration_ms,
                "logs": []
            }

    def execute_by_code(self, skill_code: str, input_payload: dict,
                        parent_execution_code: str = None) -> dict:
        """
        通过 skill_code 执行技能（供 MixedExecutor 调用）
        """
        skill = SkillService.get_skill_by_code(self.db, skill_code)
        if not skill:
            return {"success": False, "error": f"技能不存在: {skill_code}"}

        return self.execute(
            skill.skill_id,
            input_payload,
            created_via="workflow" if parent_execution_code else "manual"
        )

    def _validate_input(self, input_schema: dict, input_payload: dict) -> dict:
        """
        JSON Schema 输入校验
        """
        if not input_schema or not input_payload:
            return {"valid": True}
        return validate_input(input_payload, input_schema)
