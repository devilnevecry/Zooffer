from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.db.models import Notification


def create_notification(
    db: AsyncSession,
    user_id: UUID,
    *,
    category: str,
    title: str,
    body: str = "",
    data: dict[str, Any] | None = None,
) -> Notification:
    """Create an in-app notification row.

    Telegram/email workers use the same row, so it is kept even when the user has
    disabled the in-app channel. The notifications API filters hidden categories.
    """
    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        category=category,
        title=title[:160],
        body=body[:600],
        data=data,
    )
    db.add(notification)
    return notification


def listing_moderated(
    db: AsyncSession,
    *,
    owner_id: UUID,
    listing_slug: str,
    listing_public_id: UUID,
    approved: bool,
    reason: str,
) -> Notification:
    return create_notification(
        db,
        owner_id,
        category="listing_moderation",
        title="Объявление опубликовано" if approved else "Объявление отклонено",
        body=(
            "Объявление прошло проверку и уже доступно в поиске."
            if approved
            else f"Причина: {reason.strip()}"
        ),
        data={
            "listing_slug": listing_slug,
            "listing_public_id": str(listing_public_id),
        },
    )


def support_reply(
    db: AsyncSession, *, user_id: UUID, ticket_public_id: UUID, subject: str
) -> Notification:
    return create_notification(
        db,
        user_id,
        category="support",
        title="Ответ службы поддержки",
        body=f"По обращению «{subject}» добавлен ответ.",
        data={"support_ticket_public_id": str(ticket_public_id)},
    )
