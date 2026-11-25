from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.schemas.video import PublicVideoView, VideoCreateRequest, VideoListResponse
from zooffer.services import video_service

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", status_code=201)
async def create_video(payload: VideoCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    v = await video_service.create_video(db, user, payload)
    return await video_service.video_to_public(db, v)


@router.get("")
async def list_videos(db: DbSession, limit: int = Query(default=50, le=200)) -> VideoListResponse:
    videos = await video_service.list_videos(db, limit=limit)
    items = [PublicVideoView(**await video_service.video_to_public(db, v)) for v in videos]
    return VideoListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_video(public_id: uuid.UUID, db: DbSession) -> PublicVideoView:
    v = await video_service.get_video(db, public_id)
    await video_service.increment_view(db, public_id)
    return PublicVideoView(**await video_service.video_to_public(db, v))


@router.post("/{public_id}/like")
async def like_video(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    await video_service.toggle_like(db, user, public_id)
    return {"ok": True}
