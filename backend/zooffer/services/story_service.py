from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Profile, Story, StoryBookmark, StoryComment, StoryReaction


async def _get_story(db, public_id):
    s = await db.scalar(select(Story).where(Story.public_id == public_id))
    if s is None:
        raise NotFoundError("История не найдена", code="story_not_found")
    return s


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_story(db, user, payload) -> Story:
    s = Story(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        author_id=user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        tags=payload.tags,
        cover_url=payload.cover_url,
        status="draft",
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def update_story(db, user, public_id, payload) -> Story:
    s = await _get_story(db, public_id)
    if s.author_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    if payload.title is not None:
        s.title = payload.title.strip()
    if payload.body is not None:
        s.body = payload.body.strip()
    if payload.tags is not None:
        s.tags = payload.tags
    if payload.cover_url is not None:
        s.cover_url = payload.cover_url
    if payload.status is not None:
        if payload.status not in {"draft", "published"}:
            raise ValidationAppError("Некорректный статус", code="invalid_status")
        s.status = payload.status
        if payload.status == "published" and s.published_at is None:
            s.published_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(s)
    return s


async def publish_story(db, user, public_id) -> Story:
    s = await _get_story(db, public_id)
    if s.author_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    s.status = "published"
    if s.published_at is None:
        s.published_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(s)
    return s


async def list_stories(db, *, tag=None, status="published", limit=50):
    q = select(Story).where(Story.status == status)
    rows = (await db.scalars(q)).all()
    if tag:
        rows = [r for r in rows if tag in (r.tags or [])]
    rows = sorted(rows, key=lambda r: r.published_at or r.created_at, reverse=True)
    return list(rows[:limit])


async def get_story(db, public_id):
    return await _get_story(db, public_id)


async def add_comment(db, user, public_id, body) -> StoryComment:
    s = await _get_story(db, public_id)
    if s.status != "published":
        raise ValidationAppError("История не опубликована", code="not_published")
    c = StoryComment(id=uuid.uuid4(), story_id=s.id, author_id=user.id, body=body.strip())
    db.add(c)
    s.comments_count = (s.comments_count or 0) + 1
    await db.commit()
    await db.refresh(c)
    return c


async def list_comments(db, public_id) -> list[StoryComment]:
    s = await _get_story(db, public_id)
    rows = (
        await db.scalars(
            select(StoryComment)
            .where(StoryComment.story_id == s.id)
            .order_by(StoryComment.created_at)
        )
    ).all()
    return list(rows)


async def toggle_reaction(db, user, public_id) -> bool:
    s = await _get_story(db, public_id)
    existing = await db.scalar(
        select(StoryReaction).where(
            StoryReaction.story_id == s.id, StoryReaction.user_id == user.id
        )
    )
    if existing is not None:
        await db.delete(existing)
        s.reactions_count = max(0, (s.reactions_count or 0) - 1)
        await db.commit()
        return False
    r = StoryReaction(id=uuid.uuid4(), story_id=s.id, user_id=user.id)
    db.add(r)
    s.reactions_count = (s.reactions_count or 0) + 1
    await db.commit()
    return True


async def toggle_bookmark(db, user, public_id) -> bool:
    s = await _get_story(db, public_id)
    existing = await db.scalar(
        select(StoryBookmark).where(
            StoryBookmark.story_id == s.id, StoryBookmark.user_id == user.id
        )
    )
    if existing is not None:
        await db.delete(existing)
        s.bookmarks_count = max(0, (s.bookmarks_count or 0) - 1)
        await db.commit()
        return False
    b = StoryBookmark(id=uuid.uuid4(), story_id=s.id, user_id=user.id)
    db.add(b)
    s.bookmarks_count = (s.bookmarks_count or 0) + 1
    await db.commit()
    return True


async def story_to_public(db, s) -> dict:
    return {
        "public_id": s.public_id,
        "title": s.title,
        "body": s.body,
        "tags": s.tags or [],
        "status": s.status,
        "cover_url": s.cover_url,
        "reactions_count": s.reactions_count,
        "comments_count": s.comments_count,
        "bookmarks_count": s.bookmarks_count,
        "featured": s.featured,
        "published_at": s.published_at,
        "created_at": s.created_at,
        "author": {"display_name": await _owner_name(db, s.author_id)},
    }


async def story_to_owner(db, s) -> dict:
    return {
        "public_id": s.public_id,
        "title": s.title,
        "body": s.body,
        "tags": s.tags or [],
        "status": s.status,
        "cover_url": s.cover_url,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }
