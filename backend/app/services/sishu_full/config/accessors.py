"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
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
