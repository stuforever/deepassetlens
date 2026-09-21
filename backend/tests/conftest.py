import sys
from pathlib import Path

import pytest

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture(autouse=True)
def _pin_auth_off_baseline(monkeypatch):
    """批15.2 C5（协议 F④）：套件 auth-mode-agnostic——无论 .env ENABLE_AUTH 值，
    测试进程内固定 auth=0 基线（中间件与 expert_auth 在请求期读模块全局，monkeypatch
    模块属性即全覆盖）。显式测 auth=1 语义的用例（test_expert_acl/test_m02_auth）在
    用例体内自行 monkeypatch True 覆盖本基线（fixture 先于用例体执行，次序正确）。"""
    from app.core import auth as _core_auth
    monkeypatch.setattr(_core_auth, "ENABLE_AUTH", False, raising=False)


@pytest.fixture
def sample_select_sql():
    return "SELECT cust_id, cust_name FROM dim_customer LIMIT 10"


@pytest.fixture
def sample_with_sql():
    return "WITH t AS (SELECT 1 AS x) SELECT x FROM t"


@pytest.fixture
def sample_domain_query():
    return "用电客户的户号"
