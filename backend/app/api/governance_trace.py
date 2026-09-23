# -*- coding: utf-8 -*-
"""批⑥（v4§11）：运行观测——契约轨迹按 thread_id 查询（admin-gated）。

调试全后台：对话页不再承载契约/路由详情（批⓪下线），此处按 thread_id 回放
done 帧契约视图，前端 GovernanceObservatory「契约回放」以 ContractCardsPanel 渲染。
"""

from fastapi import APIRouter, Depends, HTTPException

from app.services.contract_trace import get_contract_trace

router = APIRouter()


def _admin_dep():
    from app.services.sishu_full.multi_user.context import get_current_user

    user = get_current_user()
    if user is None or not user.is_admin:
        from fastapi import HTTPException as _HE
        from fastapi import status as _status
        raise _HE(status_code=_status.HTTP_403_FORBIDDEN, detail="仅管理员可回放契约轨迹")
    return user


@router.get("/contract-traces/{thread_id}")
def get_contract_trace_route(thread_id: str, _: object = Depends(_admin_dep)):
    trace = get_contract_trace(thread_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"无该 thread_id 的契约轨迹: {thread_id}")
    return trace

