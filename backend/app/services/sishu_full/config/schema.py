"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
from typing import Any, Dict

from pydantic import BaseModel, field_validator


class LLMConfig(BaseModel):
    model: str
    provider: str = "openai"


class PathsConfig(BaseModel):
    user_data_dir: str
    knowledge_bases_dir: str
    user_log_dir: str


class AppConfig(BaseModel):
    llm: LLMConfig
    paths: PathsConfig

    @field_validator("llm", mode="before")
    @classmethod
    def ensure_llm(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("llm section must be a mapping")
        if "model" not in v:
            raise ValueError("llm.model is required")
        return v


CURRENT_SCHEMA_VERSION = 1


def migrate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    No-op migration for now; placeholder for future versioned changes.
    """
    return cfg
