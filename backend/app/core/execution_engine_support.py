"""
执行引擎 基础设施 —— 从 execution_engine.py 拆分（机械迁移，行为等价）

迁移内容：SandboxExecutor（受限沙箱执行）与 TemplateRenderer（模板渲染）。
execution_engine.py 通过 re-export 保持 debug_service/task_worker/v2_skills 兼容。
"""
import json
import re
import traceback
import logging
from datetime import datetime
from typing import Any, Dict

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
        # '__import__' 已移除（沙箱逃逸面：白名单保留即可 import os/subprocess 执行任意
        # 系统命令，令 filesystem/network 门控形同虚设）。结构化复用由宿主注入白名单模块。
        '__build_class__', '__name__',
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
    def _sanitize_module(mod):
        """C-逃逸修复：注入沙箱的模块对象做属性脱敏——模块顶部的 import（如
        traceback 顶部的 sys）会作为属性暴露，脚本可经 traceback.sys.modules['os']
        执行任意系统命令。仅复制公开函数/类，剔除解释器内部对象。"""
        import types as _types
        safe = _types.ModuleType(getattr(mod, "__name__", "sandbox_module"))
        _deny = {"sys", "builtins", "os", "subprocess", "importlib",
                 "__loader__", "__spec__", "__builtins__"}
        for name in dir(mod):
            if name.startswith("_") or name in _deny:
                continue
            try:
                setattr(safe, name, getattr(mod, name))
            except Exception:
                pass
        return safe

    @staticmethod
    def create_safe_globals(permissions: dict = None) -> dict:
        perms = permissions or {}
        safe_globals = {
            '__builtins__': SandboxExecutor._build_safe_builtins(perms),
        }
        safe_globals['json'] = SandboxExecutor._sanitize_module(json)
        safe_globals['re'] = SandboxExecutor._sanitize_module(re)
        safe_globals['datetime'] = datetime
        safe_globals['traceback'] = SandboxExecutor._sanitize_module(traceback)
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
            # 注入字典不得覆盖沙箱门控数据：__builtins__ 会整体替换受限 builtins
            # （可带回 __import__/open），__permissions__ 会篡改权限判定
            _reserved = {"__builtins__", "__permissions__"}
            safe_globals.update(
                {k: v for k, v in inject_globals.items() if k not in _reserved}
            )
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
            value = TemplateRenderer._get_nested_value(context, var_path, match.group(0))
            # P2: 非字符串值（int/float/bool 等）先转 str，否则 re.sub 的 repl 函数返回非字符串会 TypeError
            return value if isinstance(value, str) else str(value)

        return re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var, template)

    @staticmethod
    def render_to_binds(template: str, context: dict) -> tuple:
        """
        C-注入修复：{{var}} 值一律转为绑定参数而非字符串替换进 SQL 文本。
        返回 (sql_with_binds, params)。缺失键占位符绑定为字面 "{{x}}" 字符串
        （原行为是字面量留在 SQL 里，语义相同但不再有引号逃逸面）；
        dict/list 值此前会把 Python repr 拼进 SQL，现统一 JSON 字符串绑定。
        """
        import json as _json
        params = {}
        counter = {"n": 0}

        def replace_var_bind(match):
            var_path = match.group(1).strip()
            value = TemplateRenderer._get_nested_value(context, var_path, match.group(0))
            if isinstance(value, (dict, list, tuple, set)):
                value = _json.dumps(value, ensure_ascii=False, default=str)
            name = "p%d" % counter["n"]
            counter["n"] += 1
            params[name] = value if isinstance(value, str) else str(value)
            return ":" + name

        return re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var_bind, template), params

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

