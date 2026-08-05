import sys
from pathlib import Path

import pytest

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture
def sample_select_sql():
    return "SELECT cust_id, cust_name FROM dim_customer LIMIT 10"


@pytest.fixture
def sample_with_sql():
    return "WITH t AS (SELECT 1 AS x) SELECT x FROM t"


@pytest.fixture
def sample_domain_query():
    return "用电客户的户号"
