# -*- coding: utf-8 -*-
"""R5批⑳（清单安全）契约测试：LLM 传输安全三件。

- llm.utils：LOCAL_HOSTS 精确/后缀判定（localhost.attacker.com 不再误判本地）
- cloud_provider：disable_ssl_verify 需 env TUPU_ALLOW_INSECURE_SSL=1 复位才生效
- codex_provider：TLS 校验失败不再 verify=False 重试（源码锚定）
变异锚点：子串判定/免 env 生效/重试复活 → 对应测红。
"""
import inspect


def test_local_host_detection_no_substring_bypass():
    import app.services.sishu_full.services.llm.utils as u
    src = inspect.getsource(u)
    assert ".localhost" in src
    fn = u.is_local_llm_server
    for evil in ("https://localhost.attacker.com", "https://my-localhost-proxy.example.com"):
        assert fn(evil) is False, evil
    assert fn("http://localhost:11434") is True
    assert fn("http://127.0.0.1:8000") is True
    assert fn("http://sub.localhost") is True  # 真子域放行


def test_ssl_verify_needs_env_reset(monkeypatch):
    import app.services.sishu_full.services.llm.cloud_provider as cp
    monkeypatch.setattr(cp, "load_system_settings", lambda: {"disable_ssl_verify": True})
    monkeypatch.delenv("TUPU_ALLOW_INSECURE_SSL", raising=False)
    assert cp._get_aiohttp_connector() is None  # 设置在但无 env → 不生效
    monkeypatch.setenv("TUPU_ALLOW_INSECURE_SSL", "1")
    import asyncio

    async def _mk():
        return cp._get_aiohttp_connector()

    conn = asyncio.run(_mk())
    assert conn is not None  # 显式 env 复位后才生效
    if hasattr(conn, "close"):
        conn.close()


def test_codex_no_verify_false_retry():
    # 源码文件级锚定——该 provider 的 codex_auth import 为存量断裂（模块原不可导入），
    # 不在本批范围；本测只锚定 TLS 行为不回退。
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1]
           / "app/services/sishu/services/llm/provider_core/openai_codex_provider.py").read_text(encoding="utf-8")
    assert "CERTIFICATE_VERIFY_FAILED" in src
    assert "verify=False," not in src  # 实际重试调用已移除（注释提及不算）
    assert "疑似中间人" in src
