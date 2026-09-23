"""批⑥（v4§11 调试后台化）：契约轨迹持久化模型——对话 done 帧的契约视图按 thread_id
落库，供运行观测「契约回放」按 thread_id 查询（复用批⓪下线件 ContractCardsPanel 渲染）。
create_all 自动建表（新表，无迁移）。"""

from sqlalchemy import Column, DateTime, JSON, String
from sqlalchemy.sql import func

from .base import Base


class ContractTrace(Base):
    __tablename__ = "contract_traces"

    thread_id = Column(String(64), primary_key=True)
    expert_id = Column(String(64), nullable=False, default="wenshu")
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
