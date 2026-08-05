from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from qdrant_client import QdrantClient, models


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def get_qdrant_url() -> str:
    host = _env("QDRANT_HOST", "127.0.0.1")
    port = _env("QDRANT_PORT", "6333")
    return f"http://{host}:{port}"


def get_qdrant_api_key() -> str:
    return _env("QDRANT_API_KEY", "")


def is_qdrant_backend_enabled() -> bool:
    return _env("TUPU_VECTOR_BACKEND", "qdrant").strip().lower() == "qdrant"


class QdrantClientError(RuntimeError):
    pass


def _to_filter(filter_must: Optional[List[Dict[str, Any]]]) -> Optional[models.Filter]:
    if not filter_must:
        return None
    conditions = [models.FieldCondition.model_validate(item) for item in filter_must]
    return models.Filter(must=conditions)


class TupuQdrantClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or get_qdrant_url()).rstrip("/")
        self.api_key = api_key or get_qdrant_api_key()
        self.timeout = float(timeout)
        self._client = QdrantClient(
            url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def healthcheck(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def collection_info(self, collection: str) -> Optional[Dict[str, Any]]:
        try:
            info = self._client.get_collection(collection)
            return info.model_dump()
        except Exception:
            return None

    def ensure_collection(
        self,
        collection: str,
        vector_size: int,
        distance: str = "Cosine",
        recreate: bool = False,
    ) -> None:
        info = self.collection_info(collection)
        if info and not recreate:
            existing_size = (
                ((info.get("config") or {}).get("params") or {}).get("vectors", {}) or {}
            ).get("size") or info.get("vector_size")
            if existing_size and int(existing_size) != int(vector_size):
                raise QdrantClientError(
                    f"collection {collection} exists with vector_size={existing_size}, "
                    f"requested {vector_size}; pass recreate=True to drop"
                )
            return
        if info and recreate:
            self.delete_collection(collection)
        distance_map = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "euclid": models.Distance.EUCLID,
        }
        dist = distance_map.get(distance.strip().lower(), models.Distance.COSINE)
        try:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=int(vector_size), distance=dist),
            )
        except Exception as exc:
            raise QdrantClientError(str(exc)) from exc

    def delete_collection(self, collection: str) -> None:
        try:
            self._client.delete_collection(collection)
        except Exception:
            pass

    def upsert_points(
        self,
        collection: str,
        points: List[Dict[str, Any]],
        wait: bool = True,
    ) -> Dict[str, Any]:
        structs = [
            models.PointStruct(
                id=p["id"],
                vector=p.get("vector") or [],
                payload=p.get("payload") or {},
            )
            for p in points
        ]
        try:
            result = self._client.upsert(
                collection_name=collection,
                points=structs,
                wait=wait,
            )
            return result.model_dump() if hasattr(result, "model_dump") else {}
        except Exception as exc:
            raise QdrantClientError(str(exc)) from exc

    def delete_points(self, collection: str, point_ids: List[Any], wait: bool = True) -> Dict[str, Any]:
        try:
            result = self._client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(points=point_ids),
                wait=wait,
            )
            return result.model_dump() if hasattr(result, "model_dump") else {}
        except Exception as exc:
            raise QdrantClientError(str(exc)) from exc

    def get_points(
        self,
        collection: str,
        point_ids: List[Any],
        with_payload: bool = True,
        with_vectors: bool = True,
    ) -> List[Dict[str, Any]]:
        try:
            records = self._client.retrieve(
                collection_name=collection,
                ids=point_ids,
                with_payload=with_payload,
                with_vectors=with_vectors,
            )
            return [r.model_dump() for r in records]
        except Exception as exc:
            raise QdrantClientError(str(exc)) from exc

    def search_points(
        self,
        collection: str,
        vector: List[float],
        top: int = 20,
        score_threshold: Optional[float] = None,
        filter_must: Optional[List[Dict[str, Any]]] = None,
        with_payload: bool = True,
    ) -> List[Dict[str, Any]]:
        query_filter = _to_filter(filter_must)
        try:
            response = self._client.query_points(
                collection_name=collection,
                query=[float(x) for x in vector],
                limit=int(top),
                score_threshold=float(score_threshold) if score_threshold is not None else None,
                query_filter=query_filter,
                with_payload=with_payload,
            )
            return [
                {"id": p.id, "score": p.score, "payload": p.payload or {}}
                for p in response.points
            ]
        except Exception as exc:
            raise QdrantClientError(str(exc)) from exc

    def count_points(
        self,
        collection: str,
        filter_must: Optional[List[Dict[str, Any]]] = None,
        exact: bool = True,
    ) -> int:
        query_filter = _to_filter(filter_must)
        try:
            result = self._client.count(
                collection_name=collection,
                count_filter=query_filter,
                exact=exact,
            )
            return int(result.count)
        except Exception as exc:
            raise QdrantClientError(str(exc)) from exc

    def scroll_points(
        self,
        collection: str,
        limit: int = 256,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> Iterable[Dict[str, Any]]:
        offset: Optional[Any] = None
        while True:
            try:
                records, next_offset = self._client.scroll(
                    collection_name=collection,
                    limit=int(limit),
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    offset=offset,
                )
            except Exception as exc:
                raise QdrantClientError(str(exc)) from exc
            for record in records:
                yield record.model_dump()
            if next_offset is None:
                break
            offset = next_offset


__all__ = [
    "TupuQdrantClient",
    "QdrantClientError",
    "get_qdrant_url",
    "get_qdrant_api_key",
    "is_qdrant_backend_enabled",
]
