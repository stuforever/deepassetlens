# -*- coding: utf-8 -*-
"""批11深水：capabilities 平台路由——vendor capabilities_settings.py 1:1（2 端点全量）。

底层走移植件 capabilities_settings（services/config/capabilities_settings.py 批6已移植）。
挂载在 vendor 同前缀之前；vendor capabilities 路由整行摘除。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/settings")
async def get_capabilities_settings_endpoint() -> dict[str, Any]:
    from app.services.sishu.services.config.capabilities_settings import (
        capabilities_settings_dict,
    )

    return capabilities_settings_dict()


@router.put("/settings")
async def put_capabilities_settings(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.sishu.services.config.capabilities_settings import (
        save_capabilities_settings,
    )

    return save_capabilities_settings(payload)
