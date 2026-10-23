from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select, update

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.core.errors import NotFoundError
from zooffer.core.utils import utcnow
from zooffer.db.models import Notification, NotificationPreference
from zooffer.schemas.notification import (
    NotificationListView,
    NotificationView,
    UnreadCountView,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _hidden_categories(db, user_id) -> set[str]:  # type: ignore[no-untyped-def]
    rows = (
        await db.scalars(
            select(NotificationPreference.category).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.in_app.is_(False),
            )
        )
    ).all()
    return set(rows)


@router.get("", response_model=NotificationListView)
async def list_notifications(
    auth: CurrentAuth,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
) -> NotificationListView:
    hidden = await _hidden_categories(db, auth.user.id)
    query = select(Notification).where(Notification.user_id == auth.user.id)
    unread_query = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == auth.user.id, Notification.read_at.is_(None))
    )
    if hidden:
        query = query.where(Notification.category.notin_(hidden))
        unread_query = unread_query.where(Notification.category.notin_(hidden))
    rows = (
        await db.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
        )
    ).all()
    unread = await db.scalar(unread_query)
    return NotificationListView(
        items=[
            NotificationView(
                id=item.id,
                category=item.category,
                title=item.title,
                body=item.body,
                data=item.data,
                read_at=item.read_at,
                created_at=item.created_at,
            )
            for item in rows
        ],
        unread_count=int(unread or 0),
    )


@router.get("/unread-count", response_model=UnreadCountView)
async def unread_count(auth: CurrentAuth, db: DbSession) -> UnreadCountView:
    hidden = await _hidden_categories(db, auth.user.id)
    query = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == auth.user.id, Notification.read_at.is_(None))
    )
    if hidden:
        query = query.where(Notification.category.notin_(hidden))
    count = await db.scalar(query)
    return UnreadCountView(unread_count=int(count or 0))


@router.post("/{notification_id}/read", response_model=dict)
async def mark_read(
    notification_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> dict[str, bool]:
    notification = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == auth.user.id
        )
    )
    if notification is None:
        raise NotFoundError("Уведомление не найдено", code="notification_not_found")
    if notification.read_at is None:
        notification.read_at = utcnow()
        await db.commit()
    return {"ok": True}


@router.post("/read-all", response_model=UnreadCountView)
async def mark_all_read(auth: CurrentAuth, db: DbSession) -> UnreadCountView:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == auth.user.id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    await db.commit()
    return UnreadCountView(unread_count=0)
