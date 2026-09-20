# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/config/accessors.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
from typing import Callable


class ConfigAccessor:
    def __init__(self, loader: Callable[[], dict]):
        self._loader = loader

    def llm_model(self) -> str:
        cfg = self._loader()
        return str(cfg.get("llm", {}).get("model", "Pro/Flash"))

    def llm_provider(self) -> str:
        cfg = self._loader()
        return str(cfg.get("llm", {}).get("provider", "openai"))

    def user_data_dir(self) -> str:
        cfg = self._loader()
        return str(cfg.get("paths", {}).get("user_data_dir", "./data/user"))
