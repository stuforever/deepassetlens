"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/settings")
async def get_capabilities_settings_endpoint() -> dict[str, Any]:
    from app.services.sishu_full.services.config.capabilities_settings import capabilities_settings_dict

    return capabilities_settings_dict()


@router.put("/settings")
async def put_capabilities_settings(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.sishu_full.services.config.capabilities_settings import save_capabilities_settings

    return save_capabilities_settings(payload)
