from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from zooffer.api.deps import DbSession
from zooffer.config import settings
from zooffer.core.logging import get_logger

router = APIRouter(tags=["system"])
logger = get_logger("zooffer.health")


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: DbSession, response: Response) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("readiness_db_check_failed")
        response.status_code = 503
        return {"status": "unavailable", "database": "down"}
    return {"status": "ok", "database": "up"}


@router.get("/metrics")
async def metrics(authorization: str | None = Header(default=None)) -> Response:
    expected = f"Bearer {settings.metrics_token}"
    if not settings.metrics_token or authorization != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
