"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.sishu_full.services.storage import (
    LocalDiskAttachmentStore,
    get_attachment_store,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 允许在本站源 inline 预览的类型白名单：这些类型无法携带可执行脚本。
# text/html、image/svg+xml、未知类型等一律降级为 attachment + octet-stream，
# 阻断「上传 evil.html/evil.svg → 同源渲染执行脚本」的存储型 XSS 通路。
_INLINE_SAFE_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/avif",
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/webm", "audio/mp4", "audio/x-m4a",
    "video/mp4", "video/webm", "video/ogg", "video/quicktime",
    "text/plain", "text/csv", "application/json",
}


def _content_disposition(filename: str, *, disposition: str = "inline") -> str:
    """Build a Content-Disposition header that survives non-ASCII filenames.

    HTTP/1.1 headers are latin-1, so dropping a Chinese / accented filename
    straight into ``filename="..."`` blows up with UnicodeEncodeError. RFC
    6266 / RFC 5987 cover this: emit ``filename*=UTF-8''<percent-encoded>``
    plus an ASCII fallback on ``filename=`` for legacy clients.
    """
    ascii_fallback = filename.encode("ascii", errors="replace").decode("ascii")
    # Quotes / backslashes break the simple-quoted-string form; collapse them.
    ascii_fallback = ascii_fallback.replace('"', "_").replace("\\", "_")
    encoded = quote(filename, safe="")
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@router.get("/{session_id}/{attachment_id}/{filename:path}")
async def get_attachment(
    session_id: str,
    attachment_id: str,
    filename: str,
):
    """Serve a previously uploaded chat attachment.

    Responds with ``Content-Disposition: inline`` so browsers preview PDFs
    and images directly in an ``<iframe>`` / ``<img>``. For unknown types
    the browser still falls back to download, which is fine for the
    drawer's "Download" button path.
    """
    store = get_attachment_store()
    if not isinstance(store, LocalDiskAttachmentStore):
        # Future remote backends should issue a redirect to the signed URL
        # here. Local-disk is the only backend today, so this branch just
        # guards against an unexpected configuration.
        raise HTTPException(status_code=501, detail="Attachment backend not servable")

    target = store.resolve_path(
        session_id=session_id,
        attachment_id=attachment_id,
        filename=filename,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    media_type, _ = mimetypes.guess_type(target.name)
    if not media_type:
        media_type = "application/octet-stream"

    # 非 inline 安全类型（html/svg/未知后缀等）强制下载，避免同源脚本执行
    disposition = "inline"
    if media_type not in _INLINE_SAFE_TYPES:
        media_type = "application/octet-stream"
        disposition = "attachment"

    # ``inline`` lets the browser preview the file when possible while still
    # honouring the suggested filename for the drawer's download action.
    headers = {
        "Content-Disposition": _content_disposition(target.name, disposition=disposition),
        # User-uploaded data; do not let intermediaries cache it.
        "Cache-Control": "private, max-age=0, must-revalidate",
        # 禁止浏览器嗅探改判 Content-Type（否则 text/plain 也会被嗅探成 html 执行）
        "X-Content-Type-Options": "nosniff",
    }
    if disposition == "inline":
        # 沙箱化预览文档（unique origin、无脚本）：PDF 内嵌 JS 亦不执行
        headers["Content-Security-Policy"] = "sandbox"
    return FileResponse(path=str(target), media_type=media_type, headers=headers)
