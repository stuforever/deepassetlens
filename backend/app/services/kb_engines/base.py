# -*- coding: utf-8 -*-
"""④（spec D4）：四方法引擎协议——DeepTutor base.py 同构（RuntimeCheckable，hasattr 容忍）。"""
from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class RAGPipeline(Protocol):
    """引擎族稳定接缝：initialize/add_documents/search/delete。"""

    def initialize(self, kb: Dict[str, Any]) -> None: ...

    def add_documents(self, kb: Dict[str, Any], docs: List[Dict[str, Any]]) -> Dict[str, int]:
        """docs=[{doc_id, filename, text}] → {doc_id: chunk_count}。"""

    def search(self, kb: Dict[str, Any], query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """→ [{text, score, payload}]。"""

    def delete(self, kb: Dict[str, Any], doc_ids: List[str] | None = None) -> None:
        """doc_ids=None 删整库；否则按文档删（Qdrant filter delete）。"""
