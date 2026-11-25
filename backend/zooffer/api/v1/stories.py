from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.schemas.story import (
    PublicStoryView,
    StoryCommentCreateRequest,
    StoryCreateRequest,
    StoryListResponse,
    StoryOwnerView,
    StoryUpdateRequest,
)
from zooffer.services import story_service

router = APIRouter(prefix="/stories", tags=["stories"])


@router.post("", status_code=201)
async def create_story(payload: StoryCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    s = await story_service.create_story(db, user, payload)
    return StoryOwnerView(**await story_service.story_to_owner(db, s)).model_dump()


@router.get("")
async def list_stories(
    db: DbSession,
    tag: str | None = Query(default=None),
    status: str = Query(default="published"),
    limit: int = Query(default=50, le=200),
) -> StoryListResponse:
    stories = await story_service.list_stories(db, tag=tag, status=status, limit=limit)
    items = [PublicStoryView(**await story_service.story_to_public(db, s)) for s in stories]
    return StoryListResponse(items=items, meta={"total": len(items)})


@router.get("/{public_id}")
async def get_story(public_id: uuid.UUID, db: DbSession) -> PublicStoryView:
    s = await story_service.get_story(db, public_id)
    return PublicStoryView(**await story_service.story_to_public(db, s))


@router.patch("/{public_id}")
async def update_story(
    public_id: uuid.UUID, payload: StoryUpdateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    s = await story_service.update_story(db, user, public_id, payload)
    return StoryOwnerView(**await story_service.story_to_owner(db, s)).model_dump()


@router.post("/{public_id}/publish")
async def publish_story(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    s = await story_service.publish_story(db, user, public_id)
    return StoryOwnerView(**await story_service.story_to_owner(db, s)).model_dump()


@router.post("/{public_id}/comments", status_code=201)
async def add_comment(
    public_id: uuid.UUID, payload: StoryCommentCreateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    c = await story_service.add_comment(db, user, public_id, payload.body)
    return {
        "id": c.id,
        "body": c.body,
        "created_at": c.created_at,
        "author": {"display_name": await story_service._owner_name(db, c.author_id)},
    }


@router.get("/{public_id}/comments")
async def list_comments(public_id: uuid.UUID, db: DbSession) -> dict:
    comments = await story_service.list_comments(db, public_id)
    return {
        "items": [
            {
                "id": c.id,
                "body": c.body,
                "created_at": c.created_at,
                "author": {"display_name": await story_service._owner_name(db, c.author_id)},
            }
            for c in comments
        ]
    }


@router.post("/{public_id}/reactions")
async def toggle_reaction(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    active = await story_service.toggle_reaction(db, user, public_id)
    return {"active": active}


@router.post("/{public_id}/bookmarks")
async def toggle_bookmark(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    active = await story_service.toggle_bookmark(db, user, public_id)
    return {"active": active}
