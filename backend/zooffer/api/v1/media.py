from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from zooffer.core.errors import NotFoundError
from zooffer.services.media import get_storage

router = APIRouter(tags=["media"])

PUBLIC_PREFIXES = ("animals/", "partners/")


@router.get("/media/{key:path}")
async def serve_media(key: str) -> Response:
    # Private documents are never served through this public endpoint.
    if not key.startswith(PUBLIC_PREFIXES) or ".." in key:
        raise NotFoundError("Файл не найден", code="media_not_found")
    data = await get_storage().read(key)
    return Response(
        content=data,
        media_type="image/webp",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "Cross-Origin-Resource-Policy": "cross-origin",
        },
    )
