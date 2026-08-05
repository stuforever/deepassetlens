"""
调试服务
支持步进调试、断点、变量监控
"""

import uuid
import traceback
import ast
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models.scheduler import DebugSession
from app.models.skill import Skill, SkillVersion
from app.services.skill_manager import SkillService, VersionService
from app.core.skill_storage import get_skill_storage
from app.core.execution_engine import ExecutionEngineV2


class PythonStepTracer:
    """
    Python 代码步进追踪器
    利用 sys.settrace 实现逐行调试
    """

    def __init__(self):
        self.variables_history: List[Dict[str, Any]] = []
        self.current_line = 0
        self.call_stack: List[str] = []
        self.breakpoints: set = set()
        self.paused = False

    def trace_calls(self, frame, event, arg):
        if event == 'line':
            self.current_line = frame.f_lineno
            # 记录局部变量快照
            snapshot = {
                "line": self.current_line,
                "locals": {k: repr(v) for k, v in frame.f_locals.items() if not k.startswith('__')},
                "timestamp": datetime.utcnow().isoformat()
            }
            self.variables_history.append(snapshot)
            # 如果命中断点，暂停
            if self.current_line in self.breakpoints:
                self.paused = True
                return self.trace_calls
        elif event == 'call':
            self.call_stack.append(frame.f_code.co_name)
        elif event == 'return':
            if self.call_stack:
                self.call_stack.pop()
        return self.trace_calls

    def set_breakpoints(self, lines: List[int]):
        self.breakpoints = set(lines)

    def reset(self):
        self.variables_history = []
        self.current_line = 0
        self.call_stack = []
        self.paused = False


class DebugService:
    """调试服务"""

    def __init__(self, db: Session):
        self.db = db
        self.engine = ExecutionEngineV2(db)
        self._tracers: Dict[str, PythonStepTracer] = {}

    def create_session(self, skill_id: str, input_payload: dict,
                       debug_mode: str = "step", breakpoints: List[int] = None) -> str:
        """创建调试会话"""
        skill = SkillService.get_skill(self.db, uuid.UUID(skill_id))
        if not skill:
            raise ValueError(f"技能不存在: {skill_id}")

        session_code = f"debug_{uuid.uuid4().hex[:8]}"
        session = DebugSession(
            session_code=session_code,
            skill_id=uuid.UUID(skill_id),
            skill_code=skill.skill_code,
            debug_mode=debug_mode,
            input_payload=input_payload,
            status="active",
            breakpoints=breakpoints or [],
            current_step=0,
            logs=[],
            variable_snapshots={},
            execution_state={
                "phase": "initialized",
                "step_index": 0,
                "completed_steps": [],
            }
        )
        self.db.add(session)
        self.db.commit()

        # 初始化 tracer
        if skill.skill_type == "python":
            self._tracers[session_code] = PythonStepTracer()
            if breakpoints:
                self._tracers[session_code].set_breakpoints(breakpoints)

        return session_code

    def step(self, session_code: str) -> Dict[str, Any]:
        """单步执行"""
        session = self._get_session(session_code)
        if not session:
            return {"success": False, "error": "调试会话不存在"}
        if session.status != "active":
            return {"success": False, "error": f"会话状态不是 active: {session.status}"}

        skill = SkillService.get_skill(self.db, session.skill_id)
        if not skill:
            return {"success": False, "error": "技能不存在"}

        state = session.execution_state or {}
        phase = state.get("phase", "initialized")

        try:
            if skill.skill_type == "mixed":
                return self._step_mixed(session, skill, state)
            elif skill.skill_type == "python":
                return self._step_python(session, skill, state)
            else:
                # 其他类型不支持步进，直接执行
                return self._execute_single(session, skill)
        except Exception as e:
            session.status = "terminated"
            session.execution_state["phase"] = "error"
            session.execution_state["error"] = str(e)
            self.db.commit()
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def _step_mixed(self, session: DebugSession, skill: Skill, state: Dict) -> Dict[str, Any]:
        """Mixed 技能步进"""
        version = VersionService.get_version(self.db, skill.current_version_id)
        if not version:
            return {"success": False, "error": "技能没有激活版本"}

        storage = get_skill_storage()
        try:
            import yaml

            steps = (yaml.safe_load(storage.read_file(skill.skill_code, "scripts/main.yaml")) or {}).get("steps", [])
        except Exception as exc:
            return {"success": False, "error": f"读取混合技能脚本失败: {exc}"}
        step_index = state.get("step_index", 0)
        completed = state.get("completed_steps", [])

        if step_index >= len(steps):
            session.status = "completed"
            session.execution_state["phase"] = "completed"
            session.completed_at = datetime.utcnow()
            self.db.commit()
            return {
                "success": True,
                "phase": "completed",
                "message": "所有步骤已执行完毕",
                "completed_steps": completed,
            }

        step = steps[step_index]
        step_id = step.get("step_id", f"step_{step_index}")

        # 构建步骤输入
        step_input = self._resolve_step_input(step, session.input_payload or {}, state.get("step_outputs", {}))
        ref_skill_code = step.get("skill_code")

        # 执行子技能
        result = self.engine.execute_by_code(ref_skill_code, step_input, session.session_code)

        # 更新状态
        completed.append({
            "step_id": step_id,
            "skill_code": ref_skill_code,
            "success": result.get("success"),
            "output_preview": self._preview(result.get("output"))
        })

        step_outputs = state.get("step_outputs", {})
        step_outputs[step_id] = result.get("output", {})

        session.execution_state = {
            "phase": "stepping",
            "step_index": step_index + 1,
            "completed_steps": completed,
            "step_outputs": step_outputs,
            "current_step_id": step_id,
        }

        # 记录变量快照
        snapshots = session.variable_snapshots or {}
        snapshots[f"step_{step_index}"] = {
            "step_id": step_id,
            "input": step_input,
            "output": result.get("output"),
            "success": result.get("success"),
            "error": result.get("error"),
        }
        session.variable_snapshots = snapshots

        # 添加日志
        logs = session.logs or []
        logs.append({
            "type": "step_complete",
            "step_id": step_id,
            "success": result.get("success"),
            "timestamp": datetime.utcnow().isoformat(),
        })
        session.logs = logs
        session.current_step = step_index + 1

        self.db.commit()

        return {
            "success": True,
            "phase": "stepping",
            "current_step": step_index + 1,
            "total_steps": len(steps),
            "step_id": step_id,
            "step_result": result,
            "is_last_step": step_index + 1 >= len(steps),
        }

    def _step_python(self, session: DebugSession, skill: Skill, state: Dict) -> Dict[str, Any]:
        """Python 技能步进（简化版：执行一次函数调用）"""
        version = VersionService.get_version(self.db, skill.current_version_id)
        if not version:
            return {"success": False, "error": "技能没有激活版本"}

        phase = state.get("phase", "initialized")

        if phase == "initialized":
            # 第一步：准备执行
            session.execution_state = {
                **state,
                "phase": "ready",
                "message": "准备执行 Python 技能",
            }
            self.db.commit()
            return {
                "success": True,
                "phase": "ready",
                "message": "已准备好执行环境，请继续步进",
            }

        elif phase in ("ready", "stepping"):
            # 执行 Python 代码
            storage = get_skill_storage()
            try:
                script = storage.get_entrypoint_script(skill.skill_code, "python")
            except FileNotFoundError:
                return {"success": False, "error": "找不到入口脚本 scripts/main.py"}
            entrypoint = "execute"

            tracer = self._tracers.get(session.session_code)
            if tracer:
                tracer.reset()
                old_trace = sys.gettrace()
                sys.settrace(tracer.trace_calls)

            try:
                from app.core.execution_engine import SandboxExecutor
                result = SandboxExecutor.execute(
                    script=script,
                    entrypoint=entrypoint,
                    inputs=session.input_payload or {},
                    timeout=skill.timeout
                )
            finally:
                if tracer:
                    sys.settrace(old_trace)

            session.status = "completed"
            session.execution_state = {
                **state,
                "phase": "completed",
                "result": result,
            }
            session.completed_at = datetime.utcnow()

            # 记录变量快照
            if tracer and tracer.variables_history:
                snapshots = session.variable_snapshots or {}
                snapshots["execution"] = tracer.variables_history
                session.variable_snapshots = snapshots

            self.db.commit()

            return {
                "success": True,
                "phase": "completed",
                "result": result,
                "trace_summary": tracer.variables_history[-5:] if tracer else [],
            }

        return {"success": False, "error": f"未知执行阶段: {phase}"}

    def _execute_single(self, session: DebugSession, skill: Skill) -> Dict[str, Any]:
        """直接执行（不支持步进的技能类型）"""
        result = self.engine.execute(
            skill.skill_id,
            session.input_payload or {},
            created_via="debug"
        )
        session.status = "completed"
        session.execution_state["phase"] = "completed"
        session.execution_state["result"] = result
        session.completed_at = datetime.utcnow()
        self.db.commit()
        return {
            "success": True,
            "phase": "completed",
            "message": f"{skill.skill_type} 技能直接执行完成",
            "result": result,
        }

    def set_breakpoint(self, session_code: str, line_number: int):
        """设置断点"""
        session = self._get_session(session_code)
        if not session:
            return False

        breakpoints = session.breakpoints or []
        if line_number not in breakpoints:
            breakpoints.append(line_number)
            session.breakpoints = breakpoints
            self.db.commit()

        # 同步到 tracer
        tracer = self._tracers.get(session_code)
        if tracer:
            tracer.set_breakpoints(breakpoints)

        return True

    def remove_breakpoint(self, session_code: str, line_number: int):
        """移除断点"""
        session = self._get_session(session_code)
        if not session:
            return False

        breakpoints = session.breakpoints or []
        if line_number in breakpoints:
            breakpoints.remove(line_number)
            session.breakpoints = breakpoints
            self.db.commit()

        tracer = self._tracers.get(session_code)
        if tracer:
            tracer.set_breakpoints(breakpoints)

        return True

    def get_variable_snapshot(self, session_code: str) -> Dict[str, Any]:
        """获取变量快照"""
        session = self._get_session(session_code)
        if not session:
            return {"error": "会话不存在"}

        return {
            "session_code": session_code,
            "current_step": session.current_step,
            "phase": session.execution_state.get("phase") if session.execution_state else None,
            "variables": session.variable_snapshots,
        }

    def get_logs(self, session_code: str) -> List[Dict]:
        """获取执行日志"""
        session = self._get_session(session_code)
        if not session:
            return []
        return session.logs or []

    def terminate(self, session_code: str) -> bool:
        """终止调试会话"""
        session = self._get_session(session_code)
        if not session:
            return False
        session.status = "terminated"
        session.completed_at = datetime.utcnow()
        if session.execution_state:
            session.execution_state["phase"] = "terminated"
        self.db.commit()
        if session_code in self._tracers:
            del self._tracers[session_code]
        return True

    def get_session(self, session_code: str) -> Optional[DebugSession]:
        return self._get_session(session_code)

    def _get_session(self, session_code: str) -> Optional[DebugSession]:
        return self.db.query(DebugSession).filter(
            DebugSession.session_code == session_code
        ).first()

    def _resolve_step_input(self, step: dict, original_input: dict, step_results: dict) -> dict:
        """解析步骤输入（处理 input_mapping）"""
        input_mapping = step.get("input_mapping", {})
        resolved = {}
        for key, value in input_mapping.items():
            if isinstance(value, str):
                import re
                def replace_ref(match):
                    ref_step = match.group(1)
                    ref_key = match.group(2)
                    if ref_step in step_results:
                        return str(step_results[ref_step].get(ref_key, ""))
                    return match.group(0)
                resolved_value = re.sub(r'\{\{\s*(\w+)\.(\w+)\s*\}\}', replace_ref, value)
                resolved[key] = resolved_value
            else:
                resolved[key] = value
        return {**original_input, **resolved}

    def _preview(self, data: Any, max_len: int = 200) -> Any:
        """生成预览"""
        if data is None:
            return None
        s = str(data)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return data
