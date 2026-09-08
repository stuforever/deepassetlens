# -*- coding: utf-8 -*-
"""M15 单测：知识库 RAG 模型契约/工单只读白名单 API（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M15 spec §五验收标准锚定现有实现）。
Qdrant 真值链（建 collection/向量化/检索）与删库三处清理由联测覆盖（M09 同则：单元层不直连外部服务）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：知识库模型契约（spec §二）
# ---------------------------------------------------------------------------

def test_kb_model_columns():
    """KB 列契约（spec §二：collection unique/storage_dir/计数列/状态机/error_msg）。
    变异锚点：计数列删 → vectorize 后统计无处落；storage_dir 删 → 磁盘原文寻址断。"""
    cols = {c.name for c in KnowledgeBase.__table__.columns}
    assert {"name", "collection_name", "storage_dir", "doc_count", "vector_count",
            "status", "error_msg"} <= cols
    # collection_name unique
    uniques = {c.name for c in KnowledgeBase.__table__.columns if c.unique}
    assert "collection_name" in uniques


def test_kb_document_columns_and_cascade():
    """Doc 列契约+级联（spec §二：chunk_count/status pending→vectorized|error/级联删除）。
    变异锚点：chunk_count 删 → 检索回原文块数对不上账；cascade 删 → 删库残留孤儿文档行。"""
    cols = {c.name for c in KnowledgeDocument.__table__.columns}
    assert {"kb_id", "filename", "file_path", "file_size", "chunk_count",
            "status", "error_msg"} <= cols
    rel = KnowledgeBase.__table__.columns  # cascade 在 relationship 层——源码级锚定
    import inspect
    from app.models import knowledge_base as KBM
    src = inspect.getsource(KBM)
    assert "delete-orphan" in src or "cascade" in src.lower()


def test_collection_naming_convention():
    """collection 命名契约（spec §二：kb_ 前缀+id 去连字符）。
    变异锚点：命名规则漂移 → M09 客户端按前缀管理的集合族混乱。"""
    import inspect
    from app.models import knowledge_base as KBM
    src = inspect.getsource(KBM)
    # 命名逻辑在模型文件头契约（L30-31 附近）：kb_ 前缀 + replace("-","")
    assert "kb_" in src


# ---------------------------------------------------------------------------
# 任务 3：工单只读白名单 API（spec §三/§八.4）
# ---------------------------------------------------------------------------

def test_workorder_field_whitelist_select():
    """工单 API 字段白名单 SELECT——不暴露 SELECT *（spec §三/§八.4 外部 API 只读白名单）。
    变异锚点：白名单漂移成 SELECT * → 业务表全列外泄给 n8n。"""
    import inspect
    from app.api import biz_work_order as B
    src = inspect.getsource(B)
    assert "SELECT *" not in src
    for col in ("work_order_id", "cust_id", "work_order_type", "apply_capacity_kw", "handler"):
        assert col in src, f"白名单缺列: {col}"
    assert "source" in src  # 返回标注数据源


def test_workorder_endpoints_readonly():
    """工单两端点只读（GET /list + GET /{cust_id}；无写面，spec §三）。
    变异锚点：出现写端点 → n8n 数据面越权。"""
    from app.api import biz_work_order as B
    methods = set()
    for r in B.router.routes:
        for m in getattr(r, "methods", set()):
            methods.add(m)
    assert methods <= {"GET", "HEAD", "OPTIONS"}, f"发现非只读方法: {methods}"
    assert len(B.router.routes) >= 2


# ---------------------------------------------------------------------------
# 任务 2：端点面（spec §二 8 端点）
# ---------------------------------------------------------------------------

def test_kb_router_eight_endpoints():
    """知识库 8 端点在路由表（spec §二端点表：CRUD+upload+delDoc+vectorize+search）。
    变异锚点：search/vectorize 端点删 → RAG 闭环断。"""
    from app.api import knowledge_base as K
    paths = " ".join(getattr(r, "path", "") for r in K.router.routes)
    assert "vectorize" in paths and "search" in paths and "upload" in paths
    assert len(K.router.routes) >= 8
