# -*- coding: utf-8 -*-
"""④（spec D9）：kb_query 服务——search_kb MCP 工具的实现（HTTP 层语义复用：
type 分路 indexed/connected；工单域零触碰；无权限位——KB 默认平台内可用）。"""
from typing import Any, Dict


def kb_query(kb_id: str, query: str, top_k: int = 6) -> Dict[str, Any]:
    from app.core.database import SessionLocal
    from app.models.knowledge_base import KnowledgeBase
    db = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return {"error": f"知识库不存在: {kb_id}"}
        if not query or not str(query).strip():
            return {"error": "查询文本不能为空"}
        top_k = max(1, min(int(top_k or 6), 50))
        if (kb.type or "indexed") == "connected":
            from app.services.kb_engines.connected_es import ConnectedESFamily
            fam = ConnectedESFamily(dict(kb.pointer_params or {}))
        else:
            from app.services.kb_engines.qdrant_family import QdrantFamily
            fam = QdrantFamily()
        try:
            hits = fam.search({"id": kb.id}, query.strip(), top_k=top_k)
        except Exception as e:
            return {"error": f"检索失败: {e}"}
        return {
            "kb_id": kb.id, "kb_name": kb.name, "type": kb.type or "indexed",
            "query": query.strip(),
            "matches": [
                {"text": h["text"], "score": h["score"],
                 "filename": (h.get("payload") or {}).get("filename", ""),
                 "chunk_idx": (h.get("payload") or {}).get("chunk_idx", 0)}
                for h in hits
            ],
            "count": len(hits),
        }
    finally:
        db.close()


# B1（v4§八）单次请求最大检索库数（None=全库时的成本护栏）
KB_SEARCH_MAX_KBS = 10


def kb_search_filtered(query: str, kb_ids=None, top_k: int = 6) -> list:
    """按选中 kb_ids 过滤检索（B1——v4§八「检索层按选中队列过滤」）。

    契约：kb_ids None/空=全库不过滤（上限 KB_SEARCH_MAX_KBS）；不存在的 id /
    检索失败 / 无命中的库一律跳过不报错。返回块列表（同 kb_query 出参形状），
    供 freeplan prep 注入 HumanMessage（批① 附件条 📚 消费链）。
    """
    from app.core.database import SessionLocal
    from app.models.knowledge_base import KnowledgeBase
    if not query or not str(query).strip():
        return []
    db = SessionLocal()
    try:
        q = db.query(KnowledgeBase)
        if kb_ids:
            q = q.filter(KnowledgeBase.id.in_(list(kb_ids)[:KB_SEARCH_MAX_KBS]))
        else:
            q = q.limit(KB_SEARCH_MAX_KBS)
        kbs = q.all()
    finally:
        db.close()
    out = []
    for kb in kbs:
        res = kb_query(kb.id, query, top_k=top_k)
        if res.get("error") or not res.get("matches"):
            continue
        out.append(res)
    return out
