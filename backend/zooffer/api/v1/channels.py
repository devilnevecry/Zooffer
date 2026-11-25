from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.schemas.channel import (
    ChannelCreateRequest,
    ChannelListResponse,
    ChannelOwnerView,
    ChannelPostCreateRequest,
    PublicChannelView,
)
from zooffer.services import channel_service

router = APIRouter(prefix="/channels", tags=["channels"])


@router.post("", status_code=201)
async def create_channel(payload: ChannelCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    c = await channel_service.create_channel(db, user, payload)
    return ChannelOwnerView(**await channel_service.channel_to_owner(db, c)).model_dump()


@router.get("")
async def list_channels(
    db: DbSession, limit: int = Query(default=50, le=200)
) -> ChannelListResponse:
    channels = await channel_service.list_channels(db, limit=limit)
    items = [PublicChannelView(**await channel_service.channel_to_public(db, c)) for c in channels]
    return ChannelListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_channel(public_id: uuid.UUID, db: DbSession) -> PublicChannelView:
    c = await channel_service.get_channel(db, public_id)
    return PublicChannelView(**await channel_service.channel_to_public(db, c))


@router.post("/{public_id}/subscribe")
async def subscribe(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    active = await channel_service.subscribe(db, user, public_id)
    return {"subscribed": active}


@router.delete("/{public_id}/subscribe")
async def unsubscribe(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    removed = await channel_service.unsubscribe(db, user, public_id)
    return {"unsubscribed": removed}


@router.post("/{public_id}/posts", status_code=201)
async def create_post(
    public_id: uuid.UUID, payload: ChannelPostCreateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    post = await channel_service.create_post(db, user, public_id, payload.body)
    return {
        "id": post.id,
        "body": post.body,
        "created_at": post.created_at,
        "author": {"display_name": await channel_service._owner_name(db, post.author_id)},
    }


@router.get("/{public_id}/posts")
async def list_posts(public_id: uuid.UUID, db: DbSession) -> dict:
    posts = await channel_service.list_posts(db, public_id)
    return {
        "items": [
            {
                "id": p.id,
                "body": p.body,
                "created_at": p.created_at,
                "author": {"display_name": await channel_service._owner_name(db, p.author_id)},
            }
            for p in posts
        ]
    }
