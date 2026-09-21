"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from pathlib import Path

# Project root directory - central location for all path calculations
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Valid tools for investigate agent
VALID_INVESTIGATE_TOOLS = ["rag", "web_search", "none"]

# Valid tools for solve agent
VALID_SOLVE_TOOLS = [
    "web_search",
    "code_execution",
    "rag",
    "none",
    "finish",
]

# Standard stdlib log level tags.
LOG_LEVEL_TAGS = [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]
