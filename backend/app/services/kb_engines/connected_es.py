# -*- coding: utf-8 -*-
"""④（spec D6）：connected 指针族——不复制、不重建、删除永不碰外部资源。
检索透传（ES _search→结果归一化为 [{text, score, payload}]）；add_documents=显式拒绝
（指针型无摄入语义——管理页上传入口对 connected 隐藏+后端 422 双保险）。"""
from typing import Any, Dict, List


class ConnectedESFamily:
    def __init__(self, params: Dict[str, Any]):
        self.url = params.get("url")            # 如 http://127.0.0.1:11200
        self.index = params.get("index", "")
        self._client = params.get("client")     # 可注入（测试桩）

    def initialize(self, kb: Dict[str, Any]) -> None:
        pass                                    # 指针不建索引——连通性由状态报告探测

    def add_documents(self, kb, docs) -> Dict[str, int]:
        raise ValueError("指针型 KB 不支持文档摄入（不复制不重建）")

    def search(self, kb, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        import requests
        body = {"query": {"query_string": {"query": query}}, "size": top_k}
        resp = (self._client or requests).post(f"{self.url}/{self.index}/_search", json=body, timeout=10)
        # ④批2 实证修正（行为契约 §七）：指针失联（连接失败/索引不存在）→ 可读错误，不静默空结果
        if getattr(resp, "status_code", 200) >= 400:
            raise RuntimeError(f"外部检索源不可用: {self.url}/{self.index} 返回 {resp.status_code}")
        hits = resp.json().get("hits", {}).get("hits", [])
        return [{"text": str(h.get("_source", {}))[:500], "score": h.get("_score", 0),
                 "payload": {"_id": h.get("_id"), "_index": h.get("_index")}} for h in hits]

    def delete(self, kb, doc_ids=None) -> None:
        return None                             # 纪律：删除零触碰外部（A3 断言钉死）
