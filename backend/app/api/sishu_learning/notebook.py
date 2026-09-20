"""
Notebook API Router
Provides notebook creation, querying, updating, deletion, and record management functions
"""

import json
from typing import AsyncGenerator, Literal

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.sishu.agents.notebook import NotebookSummarizeAgent
from app.services.sishu.services.llm import clean_thinking_tags
from app.services.sishu.services.notebook import notebook_manager

from app.api.sishu_learning._enforce import SISHU_ROUTER_DEPS  # v4批6 执法面：require_expert(use)+?u= binding
router = APIRouter(dependencies=SISHU_ROUTER_DEPS)


def _h5_ctx(u: str, code: str = "", x_access_code: str = ""):
    """C1（M18-A）：笔记全路由用户隔离。

    u 非空时经 h5_user_guarded 校验访问码（?code= / X-Access-Code）并切到该用户的
    笔记本目录；u 缺省（桌面 admin）不受访问码约束。
    """
    from contextlib import nullcontext

    from app.services.sishu.compat.h5 import h5_user_guarded
    from app.services.sishu.compat.paths import user_context

    if not isinstance(u, str) or not u.strip():
        return nullcontext()
    return user_context(h5_user_guarded(u, code, x_access_code))


# === Request/Response Models ===


class CreateNotebookRequest(BaseModel):
    """Create notebook request"""

    name: str
    description: str = ""
    color: str = "#3B82F6"
    icon: str = "book"


class UpdateNotebookRequest(BaseModel):
    """Update notebook request"""

    name: str | None = None
    description: str | None = None
    color: str | None = None
    icon: str | None = None


class AddRecordRequest(BaseModel):
    """Add record request"""

    notebook_ids: list[str]
    record_type: Literal["solve", "question", "research", "chat", "co_writer", "tutorbot"]
    title: str
    summary: str = ""
    user_query: str
    output: str
    metadata: dict = {}
    kb_name: str | None = None


class RemoveRecordRequest(BaseModel):
    """Remove record request"""

    record_id: str


class UpdateRecordRequest(BaseModel):
    """Update an existing notebook record."""

    title: str | None = None
    summary: str | None = None
    user_query: str | None = None
    output: str | None = None
    metadata: dict | None = None
    kb_name: str | None = None


# === API Endpoints ===


async def _build_record_summary(request: AddRecordRequest) -> str:
    if request.summary.strip():
        return clean_thinking_tags(request.summary).strip()
    agent = NotebookSummarizeAgent(language=str(request.metadata.get("ui_language", "en")))
    return clean_thinking_tags(
        await agent.summarize(
            title=request.title,
            record_type=request.record_type,
            user_query=request.user_query,
            output=request.output,
            metadata=request.metadata,
        )
    ).strip()


async def _stream_add_record_with_summary(
    request: AddRecordRequest,
) -> AsyncGenerator[str, None]:
    try:
        agent = NotebookSummarizeAgent(language=str(request.metadata.get("ui_language", "en")))
        summary_parts: list[str] = []
        if request.summary.strip():
            summary = clean_thinking_tags(request.summary).strip()
            summary_parts.append(summary)
            if summary:
                yield f"data: {json.dumps({'type': 'summary_chunk', 'content': summary}, ensure_ascii=False)}\n\n"
        else:
            async for chunk in agent.stream_summary(
                title=request.title,
                record_type=request.record_type,
                user_query=request.user_query,
                output=request.output,
                metadata=request.metadata,
            ):
                if not chunk:
                    continue
                summary_parts.append(chunk)

            summary = clean_thinking_tags("".join(summary_parts)).strip()
            if summary:
                yield f"data: {json.dumps({'type': 'summary_chunk', 'content': summary}, ensure_ascii=False)}\n\n"

        summary = clean_thinking_tags("".join(summary_parts)).strip()
        result = notebook_manager.add_record(
            notebook_ids=request.notebook_ids,
            record_type=request.record_type,
            title=request.title,
            summary=summary,
            user_query=request.user_query,
            output=request.output,
            metadata=request.metadata,
            kb_name=request.kb_name,
        )
        payload = {
            "type": "result",
            "success": True,
            "summary": summary,
            "record": result["record"],
            "added_to_notebooks": result["added_to_notebooks"],
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    except Exception as exc:
        payload = {"type": "error", "detail": str(exc)}
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/list")
async def list_notebooks(
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Get all notebook list (C1: 按 u 隔离)

    Returns:
        Notebook list (includes summary information)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            notebooks = notebook_manager.list_notebooks()
        return {"notebooks": notebooks, "total": len(notebooks)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Get notebook statistics (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            stats = notebook_manager.get_statistics()
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_notebook(
    request: CreateNotebookRequest,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Create new notebook (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            notebook = notebook_manager.create_notebook(
                name=request.name,
                description=request.description,
                color=request.color,
                icon=request.icon,
            )
        return {"success": True, "notebook": notebook}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "notebook"}


@router.get("/{notebook_id}")
async def get_notebook(
    notebook_id: str,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Get notebook details (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            notebook = notebook_manager.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{notebook_id}")
async def update_notebook(
    notebook_id: str,
    request: UpdateNotebookRequest,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Update notebook information (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            notebook = notebook_manager.update_notebook(
                notebook_id=notebook_id,
                name=request.name,
                description=request.description,
                color=request.color,
                icon=request.icon,
            )
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return {"success": True, "notebook": notebook}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notebook_id}")
async def delete_notebook(
    notebook_id: str,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Delete notebook (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            success = notebook_manager.delete_notebook(notebook_id)
        if not success:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return {"success": True, "message": "Notebook deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_record")
async def add_record(
    request: AddRecordRequest,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Add record to notebook (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            summary = await _build_record_summary(request)
            result = notebook_manager.add_record(
                notebook_ids=request.notebook_ids,
                record_type=request.record_type,
                title=request.title,
                summary=summary,
                user_query=request.user_query,
                output=request.output,
                metadata=request.metadata,
                kb_name=request.kb_name,
            )
        return {
            "success": True,
            "summary": summary,
            "record": result["record"],
            "added_to_notebooks": result["added_to_notebooks"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_record_with_summary")
async def add_record_with_summary(
    request: AddRecordRequest,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """Add record to notebook and stream generated summary. (C1: 按 u 隔离)

    流式响应在 handler 返回后才迭代，因此上下文必须在生成器内部进入。
    """
    ctx = _h5_ctx(u, code or "", x_access_code or "")

    async def _guarded() -> AsyncGenerator[str, None]:
        with ctx:
            async for chunk in _stream_add_record_with_summary(request):
                yield chunk

    return StreamingResponse(
        _guarded(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/{notebook_id}/records/{record_id}")
async def remove_record(
    notebook_id: str,
    record_id: str,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """
    Remove record from notebook (C1: 按 u 隔离)
    """
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            success = notebook_manager.remove_record(notebook_id, record_id)
        if not success:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"success": True, "message": "Record removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{notebook_id}/records/{record_id}")
async def update_record(
    notebook_id: str,
    record_id: str,
    request: UpdateRecordRequest,
    u: str | None = None,
    code: str | None = None,
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
):
    """Update an existing notebook record in place. (C1: 按 u 隔离)"""
    try:
        with _h5_ctx(u, code or "", x_access_code or ""):
            updated = notebook_manager.update_record(
                notebook_id=notebook_id,
                record_id=record_id,
                title=request.title,
                summary=request.summary,
                user_query=request.user_query,
                output=request.output,
                metadata=request.metadata,
                kb_name=request.kb_name,
            )
        if not updated:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"success": True, "record": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
