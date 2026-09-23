"""sishu_full 包钩子：DEEPTUTOR_HOME 单点自举——DT_TUTOR_WORKSPACE_ROOT（.env，可相对）
解析为绝对路径注入 DEEPTUTOR_HOME；相对值锚 parents[3]=backend/。
曾被 .gitignore `_*.py` 规则吞件从未入库（R#7）——R3批 `git add -f` 入库：新克隆/CI
环境由此获得工作区根自举（vendor 树物理删除后，本包是唯一承接点，无其他包级钩子）。"""
import os
import sys
from pathlib import Path

_WS = os.getenv("DT_TUTOR_WORKSPACE_ROOT", "")
if _WS and not os.getenv("DEEPTUTOR_HOME"):
    _p = Path(_WS)
    if not _p.is_absolute():
        _p = Path(__file__).resolve().parents[3] / _WS   # 相对值锚 backend/（.env 相对根）
    os.environ["DEEPTUTOR_HOME"] = str(_p)
