# -*- coding: utf-8 -*-
"""IA 件批5：vendor llm 配置 → ③连接目录（LLMConnectionConfig）幂等同步适配层。
B1 3.2 knowledge 适配层同款模式；引擎解析链零改动（③照旧——诚实账 6 零风险方案）。
映射源结构（vendor services/config/model_catalog.py L128-201 实测）：
  catalog["services"]["llm"] = {"active_profile_id", "active_model_id",
    "profiles": [{"id","name","api_version","base_url","api_key","binding","extra_headers",
                  "models": [{"id","name","model"}]}]}
③目标字段（api/llm_admin.py L17-32 LLMConnectionCreate 实测；模型列 batch5 已 grep 复核一致）：
  name/provider/capability/description/base_url/api_path/api_key/model_name/
  is_default/enabled/temperature/max_tokens/timeout_seconds/extra_config/capabilities"""
from fastapi import APIRouter
from ..core.database import SessionLocal
from ..models.base import LLMConnectionConfig
from ..vendor.deeptutor.api.routers.settings import get_model_catalog_service

router = APIRouter(prefix="/api/v1/llm-connections")

@router.post("/sync-from-vendor")
def sync_from_vendor():
    """vendor llm 每条 profile×model → ③连接 upsert by name；③独有连接绝不删除。"""
    catalog = get_model_catalog_service().load()
    llm = catalog.get("services", {}).get("llm", {})
    active_pid, active_mid = llm.get("active_profile_id"), llm.get("active_model_id")
    db = SessionLocal()
    synced, skipped = [], []
    try:
        existing = {c.name: c for c in db.query(LLMConnectionConfig).all()}
        # E-11：③已有 default 连接（用户既有选择，如 4coding 360s/51200）时，同步行不抢
        # is_default——防双 default 使解析链落到 60s/512 模型默认行（WBS 硬门 5.7③ 实证教训）。
        # 幂等自愈：先前版本已写入的 default=True 行重跑本同步即被改回 False。
        others_default = any(c.is_default for c in existing.values())
        for profile in llm.get("profiles", []):
            for model in profile.get("models", []):
                name = f"{profile.get('name', 'Untitled Profile')}·{model.get('name', 'Untitled Model')}"
                row = existing.get(name)
                fields = dict(
                    provider="openai_compatible",          # profile.binding="openai" → ③ 同义
                    capability="chat",
                    description=f"IA件同步自教学域设置（profile {profile.get('id')}/model {model.get('id')}）",
                    base_url=profile.get("base_url", ""),
                    api_path="/chat/completions",
                    api_key=profile.get("api_key") or None,
                    model_name=model.get("model", ""),
                    is_default=(profile.get("id") == active_pid and model.get("id") == active_mid and not others_default),
                    enabled=True,
                    extra_config={"source": "vendor-sync",
                                  "profile_id": profile.get("id"),
                                  "model_id": model.get("id")},
                )
                if row is None:
                    db.add(LLMConnectionConfig(name=name, **fields))
                    synced.append({"name": name, "op": "insert"})
                else:
                    changed = {k: v for k, v in fields.items() if getattr(row, k, None) != v}
                    if changed:
                        for k, v in changed.items():
                            setattr(row, k, v)
                        synced.append({"name": name, "op": "update", "fields": sorted(changed)})
                    else:
                        skipped.append(name)
        db.commit()
        return {"synced": synced, "skipped": skipped}
    finally:
        db.close()
