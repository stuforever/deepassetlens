# -*- coding: utf-8 -*-
"""v4批4 4.1：平台沙箱客户端（sandbox-executor-manager 9385 直连，零 vendor 导入）。
线约冻结=backend/scripts/dt_baseline/v4_sandbox_wire.json（POST /run {code_b64,language}）。
语义映射：status=success→ok；program_error/runner_error→ok=False（stderr/detail 入 error）；
httpx 超时→ok=False+timeout 语义；连接失败→ok=False+runner unavailable（vendor 口径同款）。
超时/重试/资源限制语义对齐 vendor ExecRequest 面（自研实现，非源码复用）。"""
import base64
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:9385"


@dataclass
class SandboxResult:
    ok: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False
    error: str = ""
    artifacts: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "stdout": self.stdout, "stderr": self.stderr,
                "exit_code": self.exit_code, "timed_out": self.timed_out,
                "error": self.error, "artifacts": self.artifacts}


def _wrap_main(code: str) -> str:
    """平台 runner 契约：代码须定义 main()（from main import main 后调用）。
    未含 main 的用户代码自动包进 main() 体（缩进一级）并调用。"""
    if "def main(" in code:
        return code if "main()" in code.split("def main(")[-1] else code + "\n\nmain()\n"
    body = "\n".join(("    " + ln) if ln.strip() else "" for ln in code.splitlines())
    return f"def main():\n{body}\n\n\nmain()\n"


class SandboxClient:
    """平台基建直连 sandbox-executor-manager 9385（零 vendor 导入）。"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout_s: float = 300.0):
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    async def execute(self, code: str, language: str = "python",
                      files: dict[str, str] | None = None) -> SandboxResult:
        """执行 code；files 预留（平台 /run 单 code_b64——多文件场景批内登记）。"""
        del files  # 平台 /run 契约暂为单 code_b64——多文件需求出现时扩展
        payload = {
            "code_b64": base64.b64encode(_wrap_main(code).encode("utf-8")).decode("ascii"),
            "language": language,
        }
        http_timeout = httpx.Timeout(self._timeout_s + 15, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=http_timeout) as client:
                resp = await client.post(f"{self._base_url}/run", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ReadTimeout as exc:
            return SandboxResult(ok=False, error=f"runner timeout: sandbox execution exceeded "
                                                  f"{self._timeout_s}s ({type(exc).__name__})",
                                 timed_out=True)
        except httpx.HTTPError as exc:
            return SandboxResult(ok=False,
                                 error=f"runner unavailable: {type(exc).__name__}: {exc}")
        status = str(data.get("status", ""))
        stdout = str(data.get("stdout", ""))
        stderr = str(data.get("stderr", ""))
        exit_code = int(data.get("exit_code", 0) or 0)
        detail = str(data.get("detail") or "")
        ok = status == "success" and exit_code == 0
        error = "" if ok else (detail or stderr[:400] or status)
        return SandboxResult(ok=ok, stdout=stdout, stderr=stderr, exit_code=exit_code,
                             timed_out=False, error=error,
                             artifacts=list(data.get("artifacts") or []))
