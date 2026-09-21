"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from app.services.sishu_full.runtime.home import get_runtime_home

_project_root = get_runtime_home()

# Default configuration
DEFAULTS = {
    "llm": {"model": "gpt-4o-mini", "provider": "openai"},
    "paths": {
        "user_data_dir": str(_project_root / "data" / "user"),
        "knowledge_bases_dir": str(_project_root / "data" / "knowledge_bases"),
        "user_log_dir": str(_project_root / "data" / "user" / "logs"),
    },
}
