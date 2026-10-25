from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.errors import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Animal,
    ConversationParticipant,
    Listing,
    Message,
    MessageReport,
    Report,
    User,
)
from zooffer.schemas.report import ReportCreateRequest, ReportView


async def _report_target(db: AsyncSession, reporter: User, payload: ReportCreateRequest) -> None:
    target = payload.target_public_id

    if payload.target_type == "listing":
        listing = await db.scalar(
            select(Listing).where(Listing.public_id == target, Listing.deleted_at.is_(None))
        )
        if listing is None:
            raise NotFoundError("Объявление не найдено", code="listing_not_found")
        if listing.owner_id == reporter.id:
            raise ValidationAppError(
                "Нельзя пожаловаться на собственное объявление", code="self_report"
            )
        return

    if payload.target_type == "animal":
        animal = await db.scalar(
            select(Animal).where(Animal.public_id == target, Animal.archived_at.is_(None))
        )
        if animal is None:
            raise NotFoundError("Животное не найдено", code="animal_not_found")
        if animal.owner_id == reporter.id:
            raise ValidationAppError(
                "Нельзя пожаловаться на собственное животное", code="self_report"
            )
        return

    if payload.target_type == "user":
        user = await db.scalar(select(User).where(User.public_id == target))
        if user is None:
            raise NotFoundError("Пользователь не найден", code="user_not_found")
        if user.id == reporter.id:
            raise ValidationAppError(
                "Нельзя пожаловаться на собственный профиль", code="self_report"
            )
        return

    message = await db.get(Message, target)
    if message is None or message.deleted_at is not None:
        raise NotFoundError("Сообщение не найдено", code="message_not_found")
    participant = await db.scalar(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id == message.conversation_id,
            ConversationParticipant.user_id == reporter.id,
        )
    )
    if participant is None:
        # Do not reveal whether a conversation exists to non-participants.
        raise NotFoundError("Сообщение не найдено", code="message_not_found")
    if message.sender_id == reporter.id:
        raise ValidationAppError("Нельзя пожаловаться на собственное сообщение", code="self_report")
    duplicate = await db.scalar(
        select(MessageReport.id).where(
            MessageReport.message_id == message.id,
            MessageReport.reporter_id == reporter.id,
        )
    )
    if duplicate is not None:
        raise ConflictError("Жалоба на это сообщение уже отправлена", code="report_exists")


async def create_report(
    db: AsyncSession, reporter: User, payload: ReportCreateRequest
) -> ReportView:
    await _report_target(db, reporter, payload)
    now = utcnow()
    if payload.target_type == "message":
        db.add(
            MessageReport(
                id=uuid4(),
                message_id=payload.target_public_id,
                reporter_id=reporter.id,
                reason=payload.reason,
                details=payload.details,
                status="open",
                created_at=now,
            )
        )
    report = Report(
        id=uuid4(),
        reporter_id=reporter.id,
        target_type=payload.target_type,
        target_public_id=str(payload.target_public_id),
        reason=payload.reason,
        details=payload.details,
        status="open",
        created_at=now,
    )
    db.add(report)
    await db.commit()
    return ReportView(
        id=report.id,
        target_type=report.target_type,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
    )
