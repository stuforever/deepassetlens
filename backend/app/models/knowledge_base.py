"""自定义知识库数据模型（RAG：上传文档 -> 向量化 -> 检索增强）

复用现有基础设施：
- Qdrant (TupuQdrantClient) 存向量，每个 KB 一个 collection
- semantic_retrieval.embed_texts 做文本嵌入
- 文档原文存磁盘 backend/data/kb_documents/{kb_id}/
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class KnowledgeBase(Base):
    """自定义知识库：对应一个 Qdrant collection"""
    __tablename__ = "kg_knowledge_base"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    # Qdrant collection 名（kb_ 前缀 + id 去掉连字符，保证合法）
    collection_name = Column(String(120), nullable=False, unique=True)
    # 文档存储目录名（= kb_id）
    storage_dir = Column(String(36), nullable=False)

    doc_count = Column(Integer, nullable=False, default=0)
    vector_count = Column(Integer, nullable=False, default=0)
    # ready / processing / error / degraded（④：stale/degraded 为应用层语义）
    status = Column(String(20), nullable=False, default="ready")
    error_msg = Column(Text, nullable=True)

    # ===== ④文档知识库（spec §四）：6 列演进（indexed 现网语义等值） =====
    # indexed（自建索引）| connected（外部指针）
    type = Column(String(20), nullable=False, default="indexed")
    # qdrant | connected_es
    rag_provider = Column(String(40), nullable=False, default="qdrant")
    # connected 型连接参数（url/index 等）；indexed 必空（建库白名单 422）
    pointer_params = Column(JSON, nullable=True)
    # 签名三因子快照（嵌入模型名/维度/分块参数）——reconcile 对账依据
    embedding_signature = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documents = relationship(
        "KnowledgeDocument", back_populates="kb", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_knowledge_base_name', 'name'),
    )


class KnowledgeDocument(Base):
    """知识库文档：一个文件 = 多个向量分块"""
    __tablename__ = "kg_knowledge_document"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    kb_id = Column(String(36), ForeignKey("kg_knowledge_base.id", ondelete="CASCADE"), nullable=False, index=True)

    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)  # 磁盘绝对路径
    file_size = Column(Integer, nullable=False, default=0)
    # 向量分块数（vectorize 后更新）
    chunk_count = Column(Integer, nullable=False, default=0)
    # pending / vectorized / error / stale（④：stale=签名失配待重嵌）
    status = Column(String(20), nullable=False, default="pending")
    error_msg = Column(Text, nullable=True)

    # ===== ④文档知识库（spec §四 + 计划级精确化第 4 列） =====
    checksum = Column(String(64), nullable=True)          # 文件内容 sha256（解析缓存键）
    parse_cache_key = Column(String(128), nullable=True)  # 解析器缓存键
    # 写入时的 KB 签名快照（reconcile 对账依据——计划级精确化：对账快照无处安放）
    embedding_signature = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    kb = relationship("KnowledgeBase", back_populates="documents")

    __table_args__ = (
        Index('idx_knowledge_document_kb', 'kb_id'),
    )
