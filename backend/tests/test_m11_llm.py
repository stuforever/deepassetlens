# -*- coding: utf-8 -*-
"""M11 单测：连接池模型契约/密钥占位符/默认连接选择/静默降级（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M11 spec §八验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.base import LLMConnectionConfig  # noqa: E402


@pytest.fixture()
def llm_db():
    from app.core.database import SessionLocal
    d = SessionLocal()
    yield d
    d.close()


# ---------------------------------------------------------------------------
# 模型契约（spec §三）
# ---------------------------------------------------------------------------

def test_connection_model_contract():
    """连接池列契约+默认值（spec §三：capability 分池/api_path/密钥占位符语义/is_default）。
    变异锚点：capability 列删 → chat/embedding 分池断；api_key 列删 → 密钥无处存。"""
    cols = {c.name for c in LLMConnectionConfig.__table__.columns}
    assert {"name", "provider", "capability", "base_url", "api_path", "api_key",
            "model_name", "is_default", "enabled"} <= cols
    assert LLMConnectionConfig.__table__.c.provider.default.arg == "openai_compatible"
    assert LLMConnectionConfig.__table__.c.api_path.default.arg == "/chat/completions"
    assert LLMConnectionConfig.__table__.c.capability.default.arg == "chat"


# ---------------------------------------------------------------------------
# 密钥占位符解析（spec §四/§八.2）
# ---------------------------------------------------------------------------

def test_resolve_api_key_env_placeholder(monkeypatch):
    """${ENV} 占位符：环境变量解析/明文直传/缺失→空串。
    变异锚点：占位符解析删 → 生产密钥被迫落库。"""
    from app.services.llm_client import resolve_connection_api_key
    monkeypatch.setenv("M11_TEST_KEY", "sk-secret-123")
    assert resolve_connection_api_key("${M11_TEST_KEY}") == "sk-secret-123"
    assert resolve_connection_api_key("sk-plain-key") == "sk-plain-key"
    monkeypatch.delenv("M11_MISSING_KEY", raising=False)
    assert resolve_connection_api_key("${M11_MISSING_KEY}") == ""
    assert resolve_connection_api_key(None) == ""
    assert resolve_connection_api_key("") == ""


# ---------------------------------------------------------------------------
# 默认连接选择（spec §四/§八.1）
# ---------------------------------------------------------------------------

def test_get_default_connection_none_silent():
    """无可用连接 → None（静默降级 warning 不抛，spec §四/§八.4）。
    变异锚点：降级分支抛异常 → 上层装配无兜底机会。"""
    from app.services.llm_client import get_default_llm_connection
    res = get_default_llm_connection("m11_nonexistent_capability")
    assert res is None


def test_get_default_connection_prefers_is_default(llm_db):
    """enabled+capability 双过滤；is_default 排序取首（spec §四选择契约）。
    库内可能已有生产默认连接（如 3agent）——宽容断言锚定契约本身。
    变异锚点：is_default 排序删 → 返回非默认连接（spec §八.1）。"""
    from app.services.llm_client import get_default_llm_connection
    import uuid
    tag = f"m11{uuid.uuid4().hex[:6]}"
    c1 = LLMConnectionConfig(name=f"{tag}a", capability="chat", base_url="http://x",
                             model_name="m1", enabled=True, is_default=False)
    c2 = LLMConnectionConfig(name=f"{tag}b", capability="chat", base_url="http://x",
                             model_name="m2", enabled=True, is_default=True)
    llm_db.add_all([c1, c2])
    llm_db.commit()
    try:
        res = get_default_llm_connection("chat")
        assert res is not None
        assert res.capability == "chat"          # capability 过滤生效
        assert (res.enabled or 0) in (1, True)   # enabled 过滤生效
        assert res.is_default in (True, 1)       # is_default 排序取首（不指定具体行——库内默认连接优先合理）
    finally:
        for c in (c1, c2):
            llm_db.delete(c)
        llm_db.commit()


def test_get_connection_by_id_filters_capability(llm_db):
    """按 id 显式选择：enabled+capability 双过滤（spec §四）。
    变异锚点：capability 过滤删 → chat 场景错拿 embedding 连接。"""
    from app.services.llm_client import get_llm_connection_by_id
    import uuid
    tag = f"m11x{uuid.uuid4().hex[:6]}"
    c = LLMConnectionConfig(name=tag, capability="embedding", base_url="http://x",
                            model_name="m3", enabled=True, is_default=False)
    llm_db.add(c)
    llm_db.commit()
    try:
        # capability 不匹配 → None
        assert get_llm_connection_by_id(str(c.id), "chat") is None
        # 匹配 → 命中
        hit = get_llm_connection_by_id(str(c.id), "embedding")
        assert hit is not None and hit.name == tag
    finally:
        llm_db.delete(c)
        llm_db.commit()
