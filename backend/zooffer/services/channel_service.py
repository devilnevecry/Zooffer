from __future__ import annotations

import uuid

from sqlalchemy import select

from zooffer.core.errors import ForbiddenError, NotFoundError
from zooffer.db.models import Channel, ChannelPost, ChannelSubscription, Profile


async def _get_channel(db, public_id):
    c = await db.scalar(select(Channel).where(Channel.public_id == public_id))
    if c is None:
        raise NotFoundError("Канал не найден", code="channel_not_found")
    return c


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_channel(db, user, payload) -> Channel:
    c = Channel(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        owner_id=user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        status="active",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def list_channels(db, *, limit=50):
    rows = (await db.scalars(select(Channel).where(Channel.status == "active"))).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def get_channel(db, public_id):
    return await _get_channel(db, public_id)


async def subscribe(db, user, public_id) -> bool:
    c = await _get_channel(db, public_id)
    existing = await db.scalar(
        select(ChannelSubscription).where(
            ChannelSubscription.channel_id == c.id, ChannelSubscription.user_id == user.id
        )
    )
    if existing is not None:
        return False
    sub = ChannelSubscription(id=uuid.uuid4(), channel_id=c.id, user_id=user.id)
    db.add(sub)
    await db.commit()
    return True


async def unsubscribe(db, user, public_id) -> bool:
    c = await _get_channel(db, public_id)
    existing = await db.scalar(
        select(ChannelSubscription).where(
            ChannelSubscription.channel_id == c.id, ChannelSubscription.user_id == user.id
        )
    )
    if existing is None:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def create_post(db, user, public_id, body) -> ChannelPost:
    c = await _get_channel(db, public_id)
    if c.owner_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    post = ChannelPost(id=uuid.uuid4(), channel_id=c.id, author_id=user.id, body=body.strip())
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def list_posts(db, public_id):
    c = await _get_channel(db, public_id)
    rows = (
        await db.scalars(
            select(ChannelPost)
            .where(ChannelPost.channel_id == c.id)
            .order_by(ChannelPost.created_at.desc())
        )
    ).all()
    return list(rows)


async def channel_to_public(db, c) -> dict:
    return {
        "public_id": c.public_id,
        "title": c.title,
        "description": c.description,
        "created_at": c.created_at,
        "owner": {"display_name": await _owner_name(db, c.owner_id)},
    }


async def channel_to_owner(db, c) -> dict:
    return {
        "public_id": c.public_id,
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }
