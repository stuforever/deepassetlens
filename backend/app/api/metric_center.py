import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.base import (
    Metric,
    MetricAlias,
    MetricAtom,
    MetricAtomFilter,
    MetricDerived,
    MetricDep,
    MetricDimBinding,
    MetricFilterWhitelist,
    MetricVersion,
    MetricAuditLog,
)

router = APIRouter()


def _norm36(val: Any) -> str:
    s = str(val or "").strip()
    if len(s) == 32:
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


def _now_snapshot(metric: Metric, db: Session) -> Dict[str, Any]:
    atom = db.query(MetricAtom).filter(MetricAtom.metric_id == metric.id, MetricAtom.enabled == True).first()
    atom_filters = []
    if atom:
        atom_filters = db.query(MetricAtomFilter).filter(MetricAtomFilter.atom_id == atom.id, MetricAtomFilter.enabled == True).all()
    derived = db.query(MetricDerived).filter(MetricDerived.metric_id == metric.id, MetricDerived.enabled == True).first()
    deps = db.query(MetricDep).filter(MetricDep.metric_id == metric.id).all()
    dims = db.query(MetricDimBinding).filter(MetricDimBinding.metric_id == metric.id, MetricDimBinding.enabled == True).all()
    fwh = db.query(MetricFilterWhitelist).filter(MetricFilterWhitelist.metric_id == metric.id, MetricFilterWhitelist.enabled == True).all()

    return {
        "metric": {
            "metric_code": metric.metric_code,
            "metric_name": metric.metric_name,
            "metric_name_en": metric.metric_name_en,
            "metric_type": metric.metric_type,
            "domain": metric.domain,
            "description": metric.description,
            "metric_level": getattr(metric, "metric_level", None),
            "metric_unit": getattr(metric, "metric_unit", None),
            "metric_subject": getattr(metric, "metric_subject", None),
            "stat_grain": getattr(metric, "stat_grain", None),
            "business_caliber": getattr(metric, "business_caliber", None),
            "business_owner": getattr(metric, "business_owner", None),
            "business_dept": getattr(metric, "business_dept", None),
            "requester_user": getattr(metric, "requester_user", None),
            "tech_caliber": getattr(metric, "tech_caliber", None),
            "dev_owner": getattr(metric, "dev_owner", None),
            "search_text": getattr(metric, "search_text", None),
            "similarity_threshold": getattr(metric, "similarity_threshold", None),
            "status": metric.status,
            "owner_user": metric.owner_user,
            "reviewer_user": metric.reviewer_user,
            "manager_owner": getattr(metric, "manager_owner", None),
            "version_current": metric.version_current,
            "enabled": metric.enabled,
            "created_at": metric.created_at.isoformat() if getattr(metric, "created_at", None) else None,
            "updated_at": metric.updated_at.isoformat() if getattr(metric, "updated_at", None) else None,
        },
        "aliases": [
            {"alias": a.alias, "alias_type": a.alias_type, "weight": a.weight, "enabled": a.enabled}
            for a in db.query(MetricAlias).filter(MetricAlias.metric_id == metric.id).all()
        ],
        "atom": (
            {
                "fact_entity_id": atom.fact_entity_id,
                "fact_entity_name": atom.fact_entity_name,
                "fact_table_en": atom.fact_table_en,
                "data_source_id": atom.data_source_id,
                "agg_func": atom.agg_func,
                "measure_field_en": atom.measure_field_en,
                "measure_field_cn": atom.measure_field_cn,
                "measure_data_type": atom.measure_data_type,
                "time_field_en": atom.time_field_en,
                "time_field_cn": atom.time_field_cn,
                "default_limit": atom.default_limit,
                "grain_default": atom.grain_default,
                "definition_json": atom.definition_json,
            }
            if atom
            else None
        ),
        "atom_filters": [
            {"field_full_name": f.field_full_name, "op": f.op, "value_json": f.value_json, "enabled": f.enabled}
            for f in atom_filters
        ],
        "derived": (
            {
                "config_mode": getattr(derived, "config_mode", None),
                "expr_dsl": derived.expr_dsl,
                "base_metric_id": getattr(derived, "base_metric_id", None),
                "time_period": getattr(derived, "time_period", None),
                "available_dims_json": getattr(derived, "available_dims_json", None),
                "preset_filters_json": getattr(derived, "preset_filters_json", None),
                "unit": derived.unit,
                "precision": derived.precision,
                "enabled": derived.enabled,
            }
            if derived
            else None
        ),
        "deps": [{"dep_metric_id": d.dep_metric_id, "dep_role": d.dep_role} for d in deps],
        "dim_bindings": [
            {
                "dim_entity_id": x.dim_entity_id,
                "dim_entity_name": x.dim_entity_name,
                "join_path_id": x.join_path_id,
                "join_route_status": getattr(x, "join_route_status", None),
                "join_route_json": getattr(x, "join_route_json", None),
                "join_route_updated_at": x.join_route_updated_at.isoformat() if getattr(x, "join_route_updated_at", None) else None,
                "enabled": x.enabled,
            }
            for x in dims
        ],
        "filter_whitelist": [
            {
                "field_full_name": x.field_full_name,
                "field_cn": x.field_cn,
                "data_type": x.data_type,
                "op_whitelist_json": x.op_whitelist_json,
                "enabled": x.enabled,
            }
            for x in fwh
        ],
    }


class MetricCreateRequest(BaseModel):
    metric_code: str
    metric_name: str
    metric_type: str = Field(default="atomic")
    domain: Optional[str] = None
    description: Optional[str] = None
    metric_level: Optional[str] = None
    metric_unit: Optional[str] = None
    metric_subject: Optional[str] = None
    stat_grain: Optional[str] = None
    business_caliber: Optional[str] = None
    business_owner: Optional[str] = None
    business_dept: Optional[str] = None
    requester_user: Optional[str] = None
    tech_caliber: Optional[str] = None
    dev_owner: Optional[str] = None
    similarity_threshold: Optional[float] = None
    owner_user: Optional[str] = None
    manager_owner: Optional[str] = None


class MetricUpdateRequest(BaseModel):
    metric_name: Optional[str] = None
    metric_name_en: Optional[str] = None
    metric_type: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    metric_level: Optional[str] = None
    metric_unit: Optional[str] = None
    metric_subject: Optional[str] = None
    stat_grain: Optional[str] = None
    business_caliber: Optional[str] = None
    business_owner: Optional[str] = None
    business_dept: Optional[str] = None
    requester_user: Optional[str] = None
    tech_caliber: Optional[str] = None
    dev_owner: Optional[str] = None
    similarity_threshold: Optional[float] = None
    owner_user: Optional[str] = None
    reviewer_user: Optional[str] = None
    manager_owner: Optional[str] = None
    enabled: Optional[bool] = None


class MetricAliasUpsertRequest(BaseModel):
    aliases: List[Dict[str, Any]] = Field(default_factory=list)


class AtomUpsertRequest(BaseModel):
    fact_entity_id: str
    fact_entity_name: Optional[str] = None
    fact_table_en: Optional[str] = None
    data_source_id: Optional[str] = None
    agg_func: str
    measure_field_en: Optional[str] = None
    measure_field_cn: Optional[str] = None
    measure_data_type: Optional[str] = None
    time_field_en: str
    time_field_cn: Optional[str] = None
    default_limit: int = 200
    grain_default: str = "day"
    definition_json: Dict[str, Any] = Field(default_factory=dict)


class AtomFiltersUpsertRequest(BaseModel):
    filters: List[Dict[str, Any]] = Field(default_factory=list)


class DerivedUpsertRequest(BaseModel):
    config_mode: Optional[str] = None
    expr_dsl: Optional[str] = None
    base_metric_id: Optional[str] = None
    time_period: Optional[str] = None
    available_dims_json: Optional[List[str]] = None
    preset_filters_json: Optional[List[Dict[str, Any]]] = None
    unit: Optional[str] = None
    precision: Optional[int] = None


class DepsUpsertRequest(BaseModel):
    deps: List[Dict[str, Any]] = Field(default_factory=list)


class DimBindingsUpsertRequest(BaseModel):
    bindings: List[Dict[str, Any]] = Field(default_factory=list)


class FilterWhitelistUpsertRequest(BaseModel):
    fields: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowActionRequest(BaseModel):
    operator: Optional[str] = None
    reason: Optional[str] = None


class RollbackRequest(BaseModel):
    version: int
    operator: Optional[str] = None
    reason: Optional[str] = None


def _build_search_text(metric: Metric, db: Session) -> str:
    aliases = [
        str(a.alias or "").strip()
        for a in db.query(MetricAlias).filter(MetricAlias.metric_id == metric.id, MetricAlias.enabled == True).all()
        if str(a.alias or "").strip()
    ]
    parts = [
        str(metric.metric_code or "").strip(),
        str(metric.metric_name or "").strip(),
        str(metric.metric_name_en or "").strip(),
        str(metric.domain or "").strip(),
        str(getattr(metric, "metric_level", "") or "").strip(),
        str(getattr(metric, "metric_unit", "") or "").strip(),
        str(getattr(metric, "metric_subject", "") or "").strip(),
        str(getattr(metric, "stat_grain", "") or "").strip(),
        str(getattr(metric, "business_caliber", "") or "").strip(),
        str(getattr(metric, "business_owner", "") or "").strip(),
        str(getattr(metric, "business_dept", "") or "").strip(),
        str(getattr(metric, "tech_caliber", "") or "").strip(),
        str(getattr(metric, "dev_owner", "") or "").strip(),
        str(metric.description or "").strip(),
        " | ".join(aliases),
    ]
    return " | ".join([p for p in parts if p])


@router.get("/metrics")
def list_metrics(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    metric_type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Metric)
    if domain:
        q = q.filter(Metric.domain == domain)
    if status:
        q = q.filter(Metric.status == status)
    if metric_type:
        q = q.filter(Metric.metric_type == metric_type)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter((Metric.metric_name.like(kw)) | (Metric.metric_code.like(kw)))
    items = q.order_by(Metric.updated_at.desc()).all()
    return {
        "code": 200,
        "data": [
            {
                "id": _norm36(x.id),
                "metric_code": x.metric_code,
                "metric_name": x.metric_name,
                "metric_type": x.metric_type,
                "domain": x.domain,
                "status": x.status,
                "version_current": x.version_current,
                "enabled": x.enabled,
                "owner_user": getattr(x, "owner_user", None),
                "business_owner": getattr(x, "business_owner", None),
                "manager_owner": getattr(x, "manager_owner", None),
                "updated_at": x.updated_at.isoformat() if x.updated_at else None,
            }
            for x in items
        ],
    }


@router.get("/metrics/{metric_id}")
def get_metric(metric_id: str, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    return {"code": 200, "data": _now_snapshot(m, db)}


@router.post("/metrics")
def create_metric(payload: MetricCreateRequest, db: Session = Depends(get_db)):
    code = (payload.metric_code or "").strip()
    name = (payload.metric_name or "").strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail="metric_code与metric_name不能为空")
    existed = db.query(Metric).filter(Metric.metric_code == code).first()
    if existed:
        raise HTTPException(status_code=400, detail="metric_code已存在")

    m = Metric(
        metric_code=code,
        metric_name=name,
        metric_type=payload.metric_type or "atomic",
        domain=payload.domain,
        description=payload.description,
        metric_level=payload.metric_level,
        metric_unit=payload.metric_unit,
        metric_subject=payload.metric_subject,
        stat_grain=payload.stat_grain,
        business_caliber=payload.business_caliber,
        business_owner=payload.business_owner,
        business_dept=payload.business_dept,
        requester_user=payload.requester_user,
        tech_caliber=payload.tech_caliber,
        dev_owner=payload.dev_owner,
        similarity_threshold=payload.similarity_threshold,
        owner_user=payload.owner_user,
        manager_owner=payload.manager_owner,
        status="draft",
        version_current=1,
        enabled=True,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    db.add(
        MetricAuditLog(
            metric_id=m.id,
            action="create",
            before_json=None,
            after_json={"metric_code": m.metric_code, "metric_name": m.metric_name},
            operator=payload.owner_user,
        )
    )
    db.commit()
    return {"code": 200, "data": {"id": _norm36(m.id), "metric_code": m.metric_code}}


@router.put("/metrics/{metric_id}")
def update_metric(metric_id: str, payload: MetricUpdateRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    before = _now_snapshot(m, db)
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    after = _now_snapshot(m, db)
    db.add(MetricAuditLog(metric_id=m.id, action="update", before_json=before, after_json=after, operator=payload.owner_user))
    db.commit()
    return {"code": 200, "data": {"id": _norm36(m.id), "metric_code": m.metric_code}}


@router.delete("/metrics/{metric_id}")
def delete_metric(metric_id: str, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    db.delete(m)
    db.commit()
    return {"code": 200, "data": {"message": "deleted"}}


@router.put("/metrics/{metric_id}/aliases")
def upsert_metric_aliases(metric_id: str, payload: MetricAliasUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")

    db.query(MetricAlias).filter(MetricAlias.metric_id == mid).delete()
    for a in payload.aliases[:200]:
        alias = str(a.get("alias") or "").strip()
        if not alias:
            continue
        db.add(
            MetricAlias(
                metric_id=mid,
                alias=alias,
                alias_type=str(a.get("alias_type") or "synonym"),
                weight=float(a.get("weight") or 1.0),
                enabled=bool(a.get("enabled", True)),
            )
        )
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.put("/metrics/{metric_id}/atom")
def upsert_metric_atom(metric_id: str, payload: AtomUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    if (m.metric_type or "") != "atomic":
        raise HTTPException(status_code=400, detail="非原子指标不能配置atom")

    atom = db.query(MetricAtom).filter(MetricAtom.metric_id == mid).first()
    if not atom:
        atom = MetricAtom(metric_id=mid, fact_entity_id=_norm36(payload.fact_entity_id), agg_func=payload.agg_func, time_field_en=payload.time_field_en)
        db.add(atom)

    for k, v in payload.dict(exclude_unset=True).items():
        setattr(atom, k, v)
    atom.fact_entity_id = _norm36(atom.fact_entity_id)
    atom.data_source_id = _norm36(atom.data_source_id) if atom.data_source_id else None
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.put("/metrics/{metric_id}/atom-filters")
def upsert_metric_atom_filters(metric_id: str, payload: AtomFiltersUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    atom = db.query(MetricAtom).filter(MetricAtom.metric_id == mid).first()
    if not atom:
        raise HTTPException(status_code=400, detail="未配置atom")

    db.query(MetricAtomFilter).filter(MetricAtomFilter.atom_id == atom.id).delete()
    for f in payload.filters[:200]:
        field_full_name = str(f.get("field_full_name") or "").strip()
        op = str(f.get("op") or "").strip()
        if not field_full_name or not op:
            continue
        db.add(
            MetricAtomFilter(
                atom_id=atom.id,
                field_full_name=field_full_name,
                op=op,
                value_json=f.get("value_json"),
                enabled=bool(f.get("enabled", True)),
            )
        )
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.put("/metrics/{metric_id}/derived")
def upsert_metric_derived(metric_id: str, payload: DerivedUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    if (m.metric_type or "") != "derived":
        raise HTTPException(status_code=400, detail="非派生指标不能配置derived")

    d = db.query(MetricDerived).filter(MetricDerived.metric_id == mid).first()
    if not d:
        d = MetricDerived(metric_id=mid, config_mode=payload.config_mode or "dsl")
        db.add(d)
    mode = (payload.config_mode or getattr(d, "config_mode", None) or "dsl").strip().lower()
    if mode not in ("dsl", "config"):
        mode = "dsl"
    d.config_mode = mode
    d.expr_dsl = (payload.expr_dsl or "").strip() if mode == "dsl" else None
    d.base_metric_id = _norm36(payload.base_metric_id) if payload.base_metric_id else None
    d.time_period = payload.time_period
    d.available_dims_json = payload.available_dims_json
    d.preset_filters_json = payload.preset_filters_json
    d.unit = payload.unit
    d.precision = payload.precision
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.put("/metrics/{metric_id}/deps")
def upsert_metric_deps(metric_id: str, payload: DepsUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    if (m.metric_type or "") != "derived":
        raise HTTPException(status_code=400, detail="非派生指标不能配置deps")

    db.query(MetricDep).filter(MetricDep.metric_id == mid).delete()
    for d in payload.deps[:50]:
        dep_id = str(d.get("dep_metric_id") or "").strip()
        if not dep_id:
            continue
        dep_role = d.get("dep_role")
        db.add(MetricDep(metric_id=mid, dep_metric_id=_norm36(dep_id), dep_role=dep_role))
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.put("/metrics/{metric_id}/dim-bindings")
def upsert_metric_dim_bindings(metric_id: str, payload: DimBindingsUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    db.query(MetricDimBinding).filter(MetricDimBinding.metric_id == mid).delete()
    for b in payload.bindings[:200]:
        dim_entity_id = str(b.get("dim_entity_id") or "").strip()
        if not dim_entity_id:
            continue
        db.add(
            MetricDimBinding(
                metric_id=mid,
                dim_entity_id=_norm36(dim_entity_id),
                dim_entity_name=b.get("dim_entity_name"),
                join_path_id=_norm36(b.get("join_path_id")) if b.get("join_path_id") else None,
                enabled=bool(b.get("enabled", True)),
            )
        )
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.put("/metrics/{metric_id}/filter-whitelist")
def upsert_metric_filter_whitelist(metric_id: str, payload: FilterWhitelistUpsertRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    db.query(MetricFilterWhitelist).filter(MetricFilterWhitelist.metric_id == mid).delete()
    for f in payload.fields[:300]:
        field_full_name = str(f.get("field_full_name") or "").strip()
        if not field_full_name:
            continue
        db.add(
            MetricFilterWhitelist(
                metric_id=mid,
                field_full_name=field_full_name,
                field_cn=f.get("field_cn"),
                data_type=f.get("data_type"),
                op_whitelist_json=f.get("op_whitelist_json"),
                enabled=bool(f.get("enabled", True)),
            )
        )
    db.commit()
    return {"code": 200, "data": {"message": "updated"}}


@router.get("/metrics/{metric_id}/versions")
def list_metric_versions(metric_id: str, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    rows = db.query(MetricVersion).filter(MetricVersion.metric_id == mid).order_by(MetricVersion.version.desc()).all()
    return {
        "code": 200,
        "data": [
            {
                "id": _norm36(x.id),
                "version": x.version,
                "status": x.status,
                "created_by": x.created_by,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in rows
        ],
    }


@router.get("/metrics/{metric_id}/versions/{version}")
def get_metric_version_snapshot(metric_id: str, version: int, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    v = int(version)
    row = db.query(MetricVersion).filter(MetricVersion.metric_id == mid, MetricVersion.version == v).first()
    if not row:
        raise HTTPException(status_code=404, detail="目标版本不存在")
    return {
        "code": 200,
        "data": {
            "metric_id": mid,
            "version": row.version,
            "status": row.status,
            "snapshot": row.snapshot_json or {},
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    }


def _snapshot_and_store(db: Session, metric: Metric, operator: Optional[str], action: str) -> MetricVersion:
    snap = _now_snapshot(metric, db)
    ver = int(metric.version_current or 1)
    mv = MetricVersion(metric_id=metric.id, version=ver, status="published", snapshot_json=snap, created_by=operator)
    db.add(mv)
    db.add(MetricAuditLog(metric_id=metric.id, action=action, before_json=None, after_json=snap, operator=operator))
    db.commit()
    db.refresh(mv)
    return mv


@router.post("/metrics/{metric_id}/submit")
def submit_metric(metric_id: str, payload: WorkflowActionRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    m.status = "reviewing"
    db.commit()
    _snapshot_and_store(db, m, payload.operator, "submit")
    return {"code": 200, "data": {"status": m.status}}


@router.post("/metrics/{metric_id}/approve")
def approve_metric(metric_id: str, payload: WorkflowActionRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    m.status = "approved"
    m.reviewer_user = payload.operator
    db.commit()
    _snapshot_and_store(db, m, payload.operator, "approve")
    return {"code": 200, "data": {"status": m.status}}


@router.post("/metrics/{metric_id}/reject")
def reject_metric(metric_id: str, payload: WorkflowActionRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    m.status = "draft"
    db.commit()
    db.add(
        MetricAuditLog(
            metric_id=m.id,
            action="reject",
            before_json=None,
            after_json={"reason": payload.reason},
            operator=payload.operator,
        )
    )
    db.commit()
    return {"code": 200, "data": {"status": m.status}}


@router.post("/metrics/{metric_id}/publish")
def publish_metric(metric_id: str, payload: WorkflowActionRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    m.status = "published"
    m.search_text = _build_search_text(m, db)
    db.commit()
    _snapshot_and_store(db, m, payload.operator, "publish")
    return {"code": 200, "data": {"status": m.status}}


@router.get("/metrics/{metric_id}/audit-logs")
def list_metric_audit_logs(metric_id: str, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    rows = db.query(MetricAuditLog).filter(MetricAuditLog.metric_id == mid).order_by(MetricAuditLog.created_at.desc()).all()
    return {
        "code": 200,
        "data": [
            {
                "id": _norm36(x.id),
                "action": x.action,
                "operator": x.operator,
                "created_at": x.created_at.isoformat() if x.created_at else None,
                "before_json": x.before_json,
                "after_json": x.after_json,
            }
            for x in rows[:200]
        ],
    }


@router.get("/metrics/{metric_id}/lineage")
def get_metric_lineage(metric_id: str, depth: int = 2, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    root = db.query(Metric).filter(Metric.id == mid).first()
    if not root:
        raise HTTPException(status_code=404, detail="指标不存在")
    max_depth = max(1, min(int(depth or 2), 5))

    all_metrics = {str(x.id): x for x in db.query(Metric).all()}
    derived_rows = {str(x.metric_id): x for x in db.query(MetricDerived).filter(MetricDerived.enabled == True).all()}
    deps = db.query(MetricDep).all()

    upstream_edges: List[Dict[str, str]] = []
    downstream_edges: List[Dict[str, str]] = []

    dep_by_metric: Dict[str, List[str]] = {}
    rev_dep: Dict[str, List[str]] = {}
    for d in deps:
        a = str(d.metric_id)
        b = str(d.dep_metric_id)
        dep_by_metric.setdefault(a, []).append(b)
        rev_dep.setdefault(b, []).append(a)

    for dm in derived_rows.values():
        base_id = str(getattr(dm, "base_metric_id", "") or "").strip()
        if base_id:
            dep_by_metric.setdefault(str(dm.metric_id), []).append(base_id)
            rev_dep.setdefault(base_id, []).append(str(dm.metric_id))

    def bfs(start: str, next_fn) -> Dict[str, int]:
        dist = {start: 0}
        q = [start]
        while q:
            cur = q.pop(0)
            if dist[cur] >= max_depth:
                continue
            for nxt in next_fn(cur):
                if nxt not in dist:
                    dist[nxt] = dist[cur] + 1
                    q.append(nxt)
        return dist

    up_dist = bfs(mid, lambda x: dep_by_metric.get(x, []))
    down_dist = bfs(mid, lambda x: rev_dep.get(x, []))

    node_ids = set(list(up_dist.keys()) + list(down_dist.keys()))
    nodes = []
    for nid in node_ids:
        mm = all_metrics.get(str(nid))
        if not mm:
            continue
        nodes.append(
            {
                "id": _norm36(mm.id),
                "label": mm.metric_name,
                "metric_code": mm.metric_code,
                "metric_type": mm.metric_type,
                "status": mm.status,
                "owner": getattr(mm, "owner_user", None) or getattr(mm, "business_owner", None) or getattr(mm, "manager_owner", None),
                "depth_up": up_dist.get(nid),
                "depth_down": down_dist.get(nid),
            }
        )

    for a, bs in dep_by_metric.items():
        if a not in node_ids:
            continue
        for b in bs:
            if b in node_ids:
                upstream_edges.append({"source": _norm36(a), "target": _norm36(b), "type": "depends_on"})
    for b, as_ in rev_dep.items():
        if b not in node_ids:
            continue
        for a in as_:
            if a in node_ids:
                downstream_edges.append({"source": _norm36(b), "target": _norm36(a), "type": "used_by"})

    edges = []
    seen = set()
    for e in upstream_edges + downstream_edges:
        key = (e["source"], e["target"], e["type"])
        if key in seen:
            continue
        seen.add(key)
        edges.append(e)

    return {"code": 200, "data": {"root_id": _norm36(root.id), "nodes": nodes, "edges": edges}}


@router.post("/metrics/{metric_id}/rollback")
def rollback_metric(metric_id: str, payload: RollbackRequest, db: Session = Depends(get_db)):
    mid = _norm36(metric_id)
    m = db.query(Metric).filter(Metric.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="指标不存在")
    target = db.query(MetricVersion).filter(MetricVersion.metric_id == mid, MetricVersion.version == payload.version).first()
    if not target:
        raise HTTPException(status_code=404, detail="目标版本不存在")
    m.version_current = int(payload.version)
    db.commit()
    db.add(
        MetricAuditLog(
            metric_id=m.id,
            action="rollback",
            before_json=None,
            after_json={"version": payload.version, "reason": payload.reason},
            operator=payload.operator,
        )
    )
    db.commit()
    return {"code": 200, "data": {"version_current": m.version_current}}
