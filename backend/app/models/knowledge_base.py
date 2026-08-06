"""自定义知识库数据模型（RAG：上传文档 -> 向量化 -> 检索增强）

复用现有基础设施：
- Qdrant (TupuQdrantClient) 存向量，每个 KB 一个 collection
- semantic_retrieval.embed_texts 做文本嵌入
- 文档原文存磁盘 backend/data/kb_documents/{kb_id}/
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
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
    # ready / processing / error
    status = Column(String(20), nullable=False, default="ready")
    error_msg = Column(Text, nullable=True)

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
    # pending / vectorized / error
    status = Column(String(20), nullable=False, default="pending")
    error_msg = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    kb = relationship("KnowledgeBase", back_populates="documents")

    __table_args__ = (
        Index('idx_knowledge_document_kb', 'kb_id'),
    )
