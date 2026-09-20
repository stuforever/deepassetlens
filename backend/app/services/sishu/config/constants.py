#!/usr/bin/env python
# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/config/constants.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""
Constants for DeepTutor
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
