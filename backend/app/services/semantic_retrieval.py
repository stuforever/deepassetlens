import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib import request as urlrequest, error as urlerror

from sqlalchemy.orm import Session

from ..models.base import (
    Entity,
    EntityRelation,
    SemanticEmbedding,
    SmartPlannerConfig,
    SourceTableRelation,
)


DEFAULT_VECTOR_MODEL_NAME = "bge-large-zh-v1.5"
DEFAULT_VECTOR_DIMENSION = 1024


LOCAL_VECTOR_MODELS: Dict[str, Dict[str, Any]] = {
    "bge-large-zh-v1.5": {
        "provider": "local",
        "model_name": "bge-large-zh-v1.5",
        "path_env": "BGE_MODEL_PATH",
        "relative_path": "models/bge-large-zh-v1.5",
        "dimension": 1024,
    },
    "bge-m3": {
        "provider": "local",
        "model_name": "bge-m3",
        "path_env": "BGE_M3_MODEL_PATH",
        "relative_path": "models/bge-m3",
        "dimension": 1024,
    },
}

REMOTE_VECTOR_MODELS: Dict[str, Dict[str, Any]] = {
    "glm-embedding-3": {
        "provider": "openai_compatible_embedding",
        "model_name": "embedding-3",
        "display_name": "GLM Embedding-3",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_path": "/embeddings",
        "api_key_env": "GLM_API_KEY",
        "dimension": 2048,
        "batch_size": 16,
    },
}


VECTOR_MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    **LOCAL_VECTOR_MODELS,
    **REMOTE_VECTOR_MODELS,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += float(x) * float(y)
        na += float(x) * float(x)
        nb += float(y) * float(y)
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _hash_text(model_name: str, text: str) -> str:
    raw = f"{model_name}\n{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "models").exists() and (parent / "backend").exists():
            return parent
    return Path(__file__).resolve().parents[4]


def _resolve_local_model_path(model_name: str) -> str:
    spec = LOCAL_VECTOR_MODELS.get(model_name) or LOCAL_VECTOR_MODELS[DEFAULT_VECTOR_MODEL_NAME]
    env_path = os.getenv(str(spec.get("path_env") or ""))
    if env_path and Path(env_path).exists():
        return str(Path(env_path))
    candidates = [
        _repo_root() / str(spec["relative_path"]),
        Path.cwd() / "models" / model_name,
        Path.cwd() / ".." / "models" / model_name,
        Path.cwd() / ".." / ".." / "models" / model_name,
    ]
    for p in candidates:
        p2 = p.resolve()
        if p2.exists():
            return str(p2)
    return str(candidates[0].resolve())


def _resolve_default_model_path() -> str:
    return _resolve_local_model_path(DEFAULT_VECTOR_MODEL_NAME)


def get_vector_model_registry() -> Dict[str, Any]:
    rows = []
    for name, spec in VECTOR_MODEL_REGISTRY.items():
        item = dict(spec)
        item["key"] = name
        if item.get("provider") == "local":
            path = _resolve_local_model_path(name)
            item["model_path"] = path
            item["model_exists"] = Path(path).exists()
        else:
            item["api_key_configured"] = bool(os.getenv(str(item.get("api_key_env") or "")))
        rows.append(item)
    return {"default": DEFAULT_VECTOR_MODEL_NAME, "models": rows}


def _normalize_vector_model_name(model_name: Optional[str]) -> str:
    name = (model_name or DEFAULT_VECTOR_MODEL_NAME).strip()
    return name if name in VECTOR_MODEL_REGISTRY else DEFAULT_VECTOR_MODEL_NAME


def get_or_init_retrieval_config(db: Session) -> Dict[str, Any]:
    cfg = db.query(SmartPlannerConfig).order_by(SmartPlannerConfig.created_at.desc()).first()
    if not cfg:
        cfg = SmartPlannerConfig(
            planner_mode="rule",
            enabled=True,
            retrieval_mode="hybrid",
            vector_model_name=DEFAULT_VECTOR_MODEL_NAME,
            vector_model_path=_resolve_default_model_path(),
            keyword_weight=0.4,
            vector_weight=0.6,
            rerank_enabled=True,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    normalized_name = _normalize_vector_model_name(cfg.vector_model_name)
    model_spec = VECTOR_MODEL_REGISTRY[normalized_name]
    if cfg.vector_model_name != normalized_name:
        cfg.vector_model_name = normalized_name
    if model_spec.get("provider") == "local" and not (cfg.vector_model_path or "").strip():
        cfg.vector_model_path = _resolve_local_model_path(normalized_name)
    if model_spec.get("provider") != "local":
        cfg.vector_model_path = ""
    db.commit()
    db.refresh(cfg)
    return {
        "retrieval_mode": (cfg.retrieval_mode or "hybrid").lower(),
        "vector_model_name": normalized_name,
        "vector_model_path": cfg.vector_model_path or (_resolve_local_model_path(normalized_name) if model_spec.get("provider") == "local" else ""),
        "vector_provider": model_spec.get("provider", "local"),
        "vector_dimension": int(model_spec.get("dimension") or DEFAULT_VECTOR_DIMENSION),
        "vector_model_spec": dict(model_spec),
        "keyword_weight": float(cfg.keyword_weight or 0.4),
        "vector_weight": float(cfg.vector_weight or 0.6),
        "rerank_enabled": bool(cfg.rerank_enabled),
    }


class _EmbeddingEngine:
    """Embedding 引擎 - 基于 LangChain Embeddings 抽象

    后端：
      - local: langchain_huggingface.HuggingFaceEmbeddings（封装 sentence_transformers）
      - remote: langchain_openai.OpenAIEmbeddings（OpenAI 兼容 /embeddings 接口）
      - hash: 兜底（测试/无依赖环境）
    """
    _inited = False
    _backend = "hash"
    _model_name = DEFAULT_VECTOR_MODEL_NAME
    _model_path = ""
    _provider = "local"
    _lc_embeddings = None  # langchain Embeddings 实例

    @classmethod
    def init(cls, model_name: str, model_path: str, provider: str = "local") -> None:
        if cls._inited and cls._model_name == model_name and cls._model_path == model_path and cls._provider == provider:
            return
        cls._inited = True
        cls._model_name = model_name
        cls._model_path = model_path
        cls._provider = provider
        cls._backend = "hash"
        cls._lc_embeddings = None

        if provider != "local":
            cls._backend = provider
            return

        # 本地后端：优先用 langchain_huggingface.HuggingFaceEmbeddings
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            cls._lc_embeddings = HuggingFaceEmbeddings(
                model_name=model_path,
                encode_kwargs={"normalize_embeddings": True},
            )
            cls._backend = "sentence_transformers"
            return
        except ImportError:
            pass
        except Exception:
            pass

        # 降级 hash 兜底
        cls._backend = "hash"

    @classmethod
    def _hash_embed(cls, text: str, dim: int = 256) -> List[float]:
        vec = [0.0] * dim
        s = (text or "").strip().lower()
        if not s:
            return vec
        for i, ch in enumerate(s):
            idx = (ord(ch) * 131 + i * 17) % dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @classmethod
    def encode(cls, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if cls._backend == "sentence_transformers" and cls._lc_embeddings is not None:
            return [list(map(float, x)) for x in cls._lc_embeddings.embed_documents(texts)]
        return [cls._hash_embed(t) for t in texts]


def _call_openai_compatible_embeddings(spec: Dict[str, Any], texts: List[str], db: Optional[Session] = None) -> List[List[float]]:
    """远程 Embedding - 基于 langchain_openai.OpenAIEmbeddings"""
    from langchain_openai import OpenAIEmbeddings
    from ..services.llm_client import resolve_connection_api_key

    api_key_env = str(spec.get("api_key_env") or "")
    api_key = os.getenv(api_key_env)
    base_url = str(spec.get("base_url") or "").rstrip("/")
    api_path = str(spec.get("api_path") or "/embeddings")
    model_name = spec.get("model_name")
    if db is not None:
        try:
            from ..models.base import LLMConnectionConfig
            conn = (
                db.query(LLMConnectionConfig)
                .filter(
                    LLMConnectionConfig.enabled == True,
                    LLMConnectionConfig.capability == "embedding",
                )
                .order_by(LLMConnectionConfig.created_at.desc())
                .first()
            )
            if conn:
                api_key = resolve_connection_api_key(conn.api_key) or api_key
                base_url = (conn.base_url or base_url).rstrip("/")
                api_path = conn.api_path or api_path
                model_name = conn.model_name or model_name
        except Exception:
            pass
    if not api_key:
        raise RuntimeError(f"remote embedding api key not configured: {api_key_env}")

    # OpenAIEmbeddings 的 base_url 需要到根（不含 /embeddings）
    if api_path != "/embeddings":
        base_url = f"{base_url}{api_path}".replace("/embeddings", "")

    embeddings = OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )
    safe_texts = [str(t or "").strip() or "empty" for t in texts]
    vectors = embeddings.embed_documents(safe_texts)
    return [list(map(float, v)) for v in vectors]


def encode_texts_with_config(db: Session, texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    cfg = get_or_init_retrieval_config(db)
    selected_model = _normalize_vector_model_name(model_name or cfg["vector_model_name"])
    spec = VECTOR_MODEL_REGISTRY[selected_model]
    provider = str(spec.get("provider") or "local")
    if provider == "openai_compatible_embedding":
        return _call_openai_compatible_embeddings(spec, [str(t or "") for t in texts], db)
    model_path = cfg.get("vector_model_path") if selected_model == cfg["vector_model_name"] else _resolve_local_model_path(selected_model)
    _EmbeddingEngine.init(selected_model, str(model_path or ""), provider="local")
    return _EmbeddingEngine.encode([str(t or "") for t in texts])


def _build_embedding_items(db: Session) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    entities = db.query(Entity).all()
    for e in entities:
        e_text = " | ".join(
            [
                e.entity_code or "",
                e.entity_name or "",
                e.entity_en_name or "",
                e.description or "",
            ]
        )
        rows.append(
            {
                "object_type": "entity",
                "object_id": str(e.id),
                "text_content": e_text,
                "extra_meta": {"entity_id": str(e.id)},
            }
        )
        props = e.properties_schema if isinstance(e.properties_schema, list) else []
        for p in props[:50]:
            name = str(p.get("name") or "")
            label = str(p.get("label") or p.get("cnName") or "")
            ptype = str(p.get("type") or "")
            fid = f"{e.id}::{name}"
            p_text = " | ".join([e.entity_name or "", e.entity_en_name or "", name, label, ptype])
            rows.append(
                {
                    "object_type": "entity_field",
                    "object_id": fid,
                    "text_content": p_text,
                    "extra_meta": {"entity_id": str(e.id), "field_name": name},
                }
            )
    relations = db.query(EntityRelation).all()
    for r in relations:
        rid = str(r.id)
        r_text = " | ".join(
            [
                r.relation_name or "",
                r.direction or "",
                r.cardinality or "",
                r.join_expr or "",
                r.description or "",
            ]
        )
        rows.append(
            {
                "object_type": "entity_relation",
                "object_id": rid,
                "text_content": r_text,
                "extra_meta": {
                    "source_entity_id": str(r.source_entity_id),
                    "target_entity_id": str(r.target_entity_id),
                },
            }
        )
    source_relations = db.query(SourceTableRelation).all()
    for r in source_relations:
        rid = str(r.id)
        txt = " | ".join(
            [
                r.main_table_en or "",
                r.main_table_cn or "",
                r.related_table_en or "",
                r.related_table_cn or "",
                r.relation_expr or "",
                r.relation_desc or "",
                r.remark or "",
            ]
        )
        rows.append(
            {
                "object_type": "source_relation",
                "object_id": rid,
                "text_content": txt,
                "extra_meta": {
                    "main_table_en": r.main_table_en,
                    "related_table_en": r.related_table_en,
                },
            }
        )
    return rows


def rebuild_semantic_index(db: Session) -> Dict[str, Any]:
    cfg = get_or_init_retrieval_config(db)
    items = _build_embedding_items(db)
    embeddings = db.query(SemanticEmbedding).all()
    existing = {(e.object_type, e.object_id): e for e in embeddings}

    texts = [x["text_content"] for x in items]
    vectors = encode_texts_with_config(db, texts, cfg["vector_model_name"])
    updated = 0
    created = 0
    keep_keys = set()
    for item, vec in zip(items, vectors):
        key = (item["object_type"], item["object_id"])
        keep_keys.add(key)
        h = _hash_text(cfg["vector_model_name"], item["text_content"])
        old = existing.get(key)
        if old:
            if old.content_hash != h:
                old.text_content = item["text_content"]
                old.model_name = cfg["vector_model_name"]
                old.content_hash = h
                old.extra_meta = item.get("extra_meta")
                updated += 1
        else:
            db.add(
                SemanticEmbedding(
                    object_type=item["object_type"],
                    object_id=item["object_id"],
                    text_content=item["text_content"],
                    embedding=[],
                    model_name=cfg["vector_model_name"],
                    content_hash=h,
                    extra_meta=item.get("extra_meta"),
                )
            )
            created += 1
    deleted = 0
    for old in embeddings:
        key = (old.object_type, old.object_id)
        if key not in keep_keys:
            db.delete(old)
            deleted += 1
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "total_items": len(items),
        "backend": _EmbeddingEngine._backend,
        "model_name": cfg["vector_model_name"],
        "model_path": cfg["vector_model_path"],
    }


def semantic_status(db: Session) -> Dict[str, Any]:
    cfg = get_or_init_retrieval_config(db)
    cnt = db.query(SemanticEmbedding).count()
    model_path = cfg["vector_model_path"]
    provider = cfg.get("vector_provider") or "local"
    return {
        "retrieval_mode": cfg["retrieval_mode"],
        "keyword_weight": cfg["keyword_weight"],
        "vector_weight": cfg["vector_weight"],
        "rerank_enabled": cfg["rerank_enabled"],
        "model_name": cfg["vector_model_name"],
        "model_path": model_path,
        "model_exists": Path(model_path).exists() if provider == "local" else True,
        "model_provider": provider,
        "model_dimension": cfg.get("vector_dimension"),
        "embedding_rows": cnt,
        "backend": _EmbeddingEngine._backend if _EmbeddingEngine._inited else "not_initialized",
        "available_models": get_vector_model_registry()["models"],
    }


def hybrid_score(keyword_score: float, semantic_score: float, cfg: Dict[str, Any]) -> float:
    mode = (cfg.get("retrieval_mode") or "hybrid").lower()
    kw = _clamp(keyword_score)
    sem = _clamp(semantic_score)
    if mode == "keyword":
        return kw
    if mode == "vector":
        return sem
    kw_w = float(cfg.get("keyword_weight") or 0.4)
    sem_w = float(cfg.get("vector_weight") or 0.6)
    total = kw_w + sem_w
    if total <= 0:
        return (kw + sem) / 2
    return _clamp((kw * kw_w + sem * sem_w) / total)


def _ensure_intent_vector(cfg: Dict[str, Any], intent: str, db: Optional[Session] = None) -> List[float]:
    if db is not None:
        vecs = encode_texts_with_config(db, [intent or ""], cfg["vector_model_name"])
        return vecs[0] if vecs else []
    _EmbeddingEngine.init(cfg["vector_model_name"], cfg["vector_model_path"], provider=cfg.get("vector_provider", "local"))
    vecs = _EmbeddingEngine.encode([intent or ""])
    return vecs[0] if vecs else []


def get_embedding_map(db: Session, object_type: str) -> Dict[str, List[float]]:
    rows = db.query(SemanticEmbedding).filter(SemanticEmbedding.object_type == object_type).all()
    out: Dict[str, List[float]] = {}
    for r in rows:
        vec = r.embedding if isinstance(r.embedding, list) else []
        out[str(r.object_id)] = [float(x) for x in vec]
    return out


def score_entities_semantic(db: Session, intent: str) -> Dict[str, float]:
    cfg = get_or_init_retrieval_config(db)
    intent_vec = _ensure_intent_vector(cfg, intent, db)
    emb_map = get_embedding_map(db, "entity")
    return {eid: _clamp((_cosine(intent_vec, vec) + 1) / 2) for eid, vec in emb_map.items()}


def score_source_relations_semantic(db: Session, intent: str) -> Dict[str, float]:
    cfg = get_or_init_retrieval_config(db)
    intent_vec = _ensure_intent_vector(cfg, intent, db)
    emb_map = get_embedding_map(db, "source_relation")
    return {rid: _clamp((_cosine(intent_vec, vec) + 1) / 2) for rid, vec in emb_map.items()}


def embed_texts(db: Session, texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    return encode_texts_with_config(db, [str(t or "") for t in texts], model_name)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return _cosine(a, b)
