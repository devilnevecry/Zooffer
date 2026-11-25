from __future__ import annotations

import uuid

from sqlalchemy import select

from zooffer.core.errors import NotFoundError
from zooffer.db.models import Profile, VideoPost


async def _get(db, public_id):
    v = await db.scalar(select(VideoPost).where(VideoPost.public_id == public_id))
    if v is None:
        raise NotFoundError("Видео не найдено", code="video_not_found")
    return v


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_video(db, user, payload) -> VideoPost:
    v = VideoPost(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        author_id=user.id,
        caption=payload.caption.strip(),
        media_key=payload.media_key,
        thumb_key=payload.thumb_key,
        status="published",
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


async def list_videos(db, *, limit=50):
    rows = (await db.scalars(select(VideoPost).where(VideoPost.status == "published"))).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def get_video(db, public_id):
    return await _get(db, public_id)


async def increment_view(db, public_id):
    v = await _get(db, public_id)
    v.views = (v.views or 0) + 1
    await db.commit()
    return v


async def toggle_like(db, user, public_id) -> bool:
    v = await _get(db, public_id)
    # simple increment (no per-user tracking for MVP)
    v.likes = (v.likes or 0) + 1
    await db.commit()
    return True


async def video_to_public(db, v) -> dict:
    return {
        "public_id": v.public_id,
        "caption": v.caption,
        "media_key": v.media_key,
        "thumb_key": v.thumb_key,
        "status": v.status,
        "views": v.views,
        "likes": v.likes,
        "created_at": v.created_at,
        "author": {"display_name": await _owner_name(db, v.author_id)},
    }
