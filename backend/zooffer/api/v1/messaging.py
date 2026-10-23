from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.schemas.messaging import (
    ConversationDetailView,
    ConversationListView,
    ConversationSummaryView,
    MessagePageView,
    MessageView,
    SendMessageRequest,
    StartInquiryRequest,
)
from zooffer.services import messaging_service

router = APIRouter(prefix="/conversations", tags=["messaging"])


@router.get("", response_model=ConversationListView)
async def list_conversations(auth: CurrentAuth, db: DbSession) -> ConversationListView:
    return await messaging_service.list_conversations(db, auth.user.id)


@router.post("", response_model=ConversationDetailView, status_code=201)
async def start_inquiry(
    payload: StartInquiryRequest, auth: CurrentAuth, db: DbSession
) -> ConversationDetailView:
    return await messaging_service.start_inquiry(
        db, auth.user, payload.listing_public_id, payload.message
    )


@router.get("/{public_id}", response_model=ConversationDetailView)
async def get_conversation(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str | None = None,
) -> ConversationDetailView:
    return await messaging_service.get_conversation(
        db, auth.user.id, public_id, limit=limit, cursor=cursor
    )


@router.get("/{public_id}/messages", response_model=MessagePageView)
async def list_messages(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str | None = None,
) -> MessagePageView:
    return await messaging_service.list_messages(
        db, auth.user.id, public_id, limit=limit, cursor=cursor
    )


@router.post("/{public_id}/messages", response_model=MessageView, status_code=201)
async def send_message(
    public_id: uuid.UUID, payload: SendMessageRequest, auth: CurrentAuth, db: DbSession
) -> MessageView:
    return await messaging_service.send_message(db, auth.user, public_id, payload.body)


@router.post("/{public_id}/read", response_model=ConversationSummaryView)
async def mark_read(
    public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> ConversationSummaryView:
    return await messaging_service.mark_read(db, auth.user.id, public_id)


@router.post("/{public_id}/block", response_model=dict)
async def block_counterpart(
    public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> dict[str, bool]:
    await messaging_service.block_counterpart(db, auth.user, public_id)
    return {"ok": True}


@router.delete("/{public_id}/block", response_model=dict)
async def unblock_counterpart(
    public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> dict[str, bool]:
    await messaging_service.unblock_counterpart(db, auth.user, public_id)
    return {"ok": True}
