from __future__ import annotations

from fastapi import APIRouter

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.core.rate_limit import limiter
from zooffer.schemas.report import ReportCreateRequest, ReportView
from zooffer.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportView, status_code=201)
async def create_report(
    payload: ReportCreateRequest, auth: CurrentAuth, db: DbSession
) -> ReportView:
    await limiter.hit(f"report:{auth.user.id}", limit=10, window_seconds=3600)
    return await report_service.create_report(db, auth.user, payload)
