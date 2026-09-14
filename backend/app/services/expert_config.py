# -*- coding: utf-8 -*-
"""专家地基①（2026-09-12 spec §四/§十）：专家卡配置服务——机制照抄 guard_config/capability_config。

TTL 5s 缓存 + get_version() + update_card()→version+1+事件落账。
fail-safe（spec §十）：卡读取失败 wenshu 特例兜底内置基线（source=builtin_baseline）；
其他专家不可用如实抛错，禁止降级成 wenshu（身份错乱比不可用更糟）。
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CACHE_TTL = 5.0
_CACHE: Dict[str, Any] = {"rows": None, "ts": 0.0, "version": None, "lock": threading.Lock()}


def _mcp_tool_registry() -> List[str]:
    """活注册表（spec R2）：MCP 工具名全集，从 GENERIC_ALLOWED_TOOLS 派生（剔除框架件
    read_file）——该白名单与 mcp_server 真实注册面强一致（P0 整改注释为证），文档数字仅快照。"""
    from app.services.query_contract import GENERIC_ALLOWED_TOOLS
    return sorted(set(GENERIC_ALLOWED_TOOLS) - {"read_file"})


def default_wenshu_card() -> Dict[str, Any]:
    """内置基线（spec §四 DEFAULT_WENSHU_CARD）：逐字段与种子卡同值。system_prompt
    引用 _BASE_ROLE 常量本体（运行时导入防环）——构造级等值，非拷贝。"""
    from app.services.tupu_deepagent import _BASE_ROLE
    return {
        "expert_id": "wenshu", "name": "数据资产探查",
        "tagline": "一句话问数 · 受控执行 · 全程可审计",
        "enabled": True, "entry_kind": "chat",
        "system_prompt": _BASE_ROLE,
        "tools": _mcp_tool_registry(),
        "skills": ["/skills/"], "memory": ["/memory/AGENTS.md"],
        "knowledge_sources": ["ontology_graph"], "llm_connection_id": None,
        "icon": "search", "description": "一句话问数 · 受控执行 · 全程可审计",
        "ui_config": {
            "placeholder": "想问什么数据？",
            "suggestions": ["统计用电客户总数", "什么是变压器",
                            "配电变压器有哪些？列出编号和名称", "用电客户数据的来源"],
            "welcome": {"title": "数据资产探查", "tagline": "一句话问数 · 受控执行 · 全程可审计"},
        },
        "version": 1,
    }


def _load_rows(force: bool = False) -> List[Dict[str, Any]]:
    """读全卡（TTL 5s，照抄 guard_config.get_policies 缓存范式）。"""
    from app.models.base import ExpertProfile
    from app.core.database import SessionLocal
    with _CACHE["lock"]:
        now = time.time()
        if not force and _CACHE["rows"] is not None and now - _CACHE["ts"] < _CACHE_TTL:
            return _CACHE["rows"]
        db = SessionLocal()
        try:
            rows = db.query(ExpertProfile).all()
            out = [{
                "expert_id": r.expert_id, "name": r.name, "tagline": r.tagline,
                "enabled": bool(r.enabled), "entry_kind": r.entry_kind,
                "system_prompt": r.system_prompt or "", "tools": r.tools or [],
                "skills": r.skills or [], "memory": r.memory or [],
                "knowledge_sources": r.knowledge_sources or [],
                "llm_connection_id": r.llm_connection_id, "icon": r.icon,
                "description": r.description, "ui_config": r.ui_config or {},
                "updated_by": r.updated_by, "updated_at": r.updated_at,
                "close_reason": r.close_reason, "version": r.version or 1,
            } for r in rows]
        finally:
            db.close()
        _CACHE["rows"] = out
        _CACHE["ts"] = now
        return out


def get_version() -> int:
    """全局专家卡版本号 = max(version)（进缓存键 #e 因子；查库异常返 0 沿 get_version 先例）。"""
    try:
        return max((r["version"] for r in _load_rows()), default=0) or 0
    except Exception:
        return 0


def get_card(expert_id: str, with_source: bool = False):
    """读单卡。fail-safe：读失败时 wenshu 兜底内置基线（source=builtin_baseline），
    其他专家抛 RuntimeError（不降级，spec §十）。"""
    try:
        rows = _load_rows()
    except Exception as e:
        if expert_id == "wenshu":
            logger.warning(f"[expert_config] 卡读取失败，wenshu 兜底内置基线: {e}")
            card = default_wenshu_card()
            return (card, "builtin_baseline") if with_source else card
        raise RuntimeError(f"专家卡服务不可用: {expert_id}") from e
    for r in rows:
        if r["expert_id"] == expert_id:
            return (r, "db") if with_source else r
    if expert_id == "wenshu":                       # 表空/行缺：同样兜底
        card = default_wenshu_card()
        return (card, "builtin_baseline") if with_source else card
    raise KeyError(expert_id)


def update_card(expert_id: str, *, updated_by: Optional[str] = None,
                close_reason: Optional[str] = None, confirm: bool = True, **fields) -> Dict[str, Any]:
    """改卡→version+1+事件落账+清缓存。enabled=False 属红级关闭：缺 close_reason→ValueError
    （API 层转 400，照抄 update_guard 语义）。"""
    from app.models.base import ExpertProfile
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        row = db.query(ExpertProfile).filter(ExpertProfile.expert_id == expert_id).first()
        if row is None:
            raise KeyError(expert_id)
        if fields.get("enabled") is False:
            reason = (close_reason or "").strip()
            if len(reason) < 10:
                raise ValueError("关停专家需填写理由（至少 10 字）")
            row.close_reason = reason[:500]
        for k, v in fields.items():
            if hasattr(row, k):
                setattr(row, k, v)
        row.updated_by = updated_by
        from sqlalchemy.sql import func as _f
        row.updated_at = _f.now()
        row.version = (row.version or 1) + 1
        db.commit()
        db.refresh(row)
        out = dict(fields)
        out.update({"expert_id": expert_id, "version": row.version})
        record_event(expert_id, "disabled" if fields.get("enabled") is False else "updated",
                     detail={"version": row.version, "fields": sorted(fields)}, updated_by=updated_by)
        _CACHE["rows"] = None
        return out
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def record_event(expert_id: str, action: str, *, detail: Optional[Dict[str, Any]] = None,
                 updated_by: Optional[str] = None) -> None:
    """写 expert_events（fire-and-forget，record_event 惯例）。"""
    def _do():
        try:
            from app.models.base import ExpertEvent
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                db.add(ExpertEvent(expert_id=expert_id[:64], action=action[:24],
                                   detail=detail, updated_by=updated_by))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[ExpertEvent] 写入失败(不阻塞主链路): {e}")
    try:
        import threading
        threading.Thread(target=_do, daemon=True).start()
    except Exception:
        _do()
