from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tests.helpers import make_published_listing, register
from zooffer.core.security import hash_email
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReport,
    Report,
    User,
    UserPrivateData,
)
from zooffer.main import app


@asynccontextmanager
async def extra_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


async def _user_by_email(db, email: str) -> User:
    user = await db.scalar(
        select(User)
        .join(UserPrivateData, UserPrivateData.user_id == User.id)
        .where(UserPrivateData.email_hash == hash_email(email))
    )
    assert user is not None
    return user


async def test_report_listing_appears_in_admin_queue(client: AsyncClient, db) -> None:
    await register(client, "owner-report@example.com")
    _, listing, _ = await make_published_listing(client)

    async with extra_client() as other:
        await register(other, "reporter@example.com")
        response = await other.post(
            "/api/v1/reports",
            json={
                "target_type": "listing",
                "target_public_id": listing["public_id"],
                "reason": "scam",
                "details": "Просят предоплату до встречи.",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "open"
        assert response.json()["target_type"] == "listing"

    stored = (await db.scalars(select(Report))).all()
    assert len(stored) == 1
    assert stored[0].target_public_id == listing["public_id"]
    assert stored[0].reason == "scam"


async def test_cannot_report_own_listing(client: AsyncClient) -> None:
    await register(client, "self-report@example.com")
    _, listing, _ = await make_published_listing(client)
    response = await client.post(
        "/api/v1/reports",
        json={
            "target_type": "listing",
            "target_public_id": listing["public_id"],
            "reason": "other",
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "self_report"


async def test_report_missing_target_is_not_found(client: AsyncClient) -> None:
    await register(client, "missing-report@example.com")
    response = await client.post(
        "/api/v1/reports",
        json={
            "target_type": "listing",
            "target_public_id": str(uuid4()),
            "reason": "spam",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "listing_not_found"


async def test_message_report_requires_participation_and_is_unique(
    client: AsyncClient, db
) -> None:
    await register(client, "chat-owner@example.com")
    async with extra_client() as reporter_client:
        await register(reporter_client, "reporter-chat@example.com")
        owner = await _user_by_email(db, "chat-owner@example.com")
        reporter = await _user_by_email(db, "reporter-chat@example.com")

        conversation = Conversation(
            id=uuid4(),
            public_id=uuid4(),
            conversation_type="match",
            last_message_at=utcnow(),
        )
        db.add(conversation)
        db.add_all(
            [
                ConversationParticipant(conversation_id=conversation.id, user_id=owner.id),
                ConversationParticipant(
                    conversation_id=conversation.id, user_id=reporter.id
                ),
            ]
        )
        message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            sender_id=owner.id,
            body="Переведите предоплату на карту.",
            created_at=utcnow(),
        )
        db.add(message)
        await db.commit()

        async with extra_client() as stranger:
            await register(stranger, "chat-stranger@example.com")
            denied = await stranger.post(
                "/api/v1/reports",
                json={
                    "target_type": "message",
                    "target_public_id": str(message.id),
                    "reason": "scam",
                },
            )
            assert denied.status_code == 404, denied.text

        first = await reporter_client.post(
            "/api/v1/reports",
            json={
                "target_type": "message",
                "target_public_id": str(message.id),
                "reason": "scam",
                "details": "Просит перевод на карту.",
            },
        )
        assert first.status_code == 201, first.text
        duplicate = await reporter_client.post(
            "/api/v1/reports",
            json={
                "target_type": "message",
                "target_public_id": str(message.id),
                "reason": "spam",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "report_exists"

        message_reports = (await db.scalars(select(MessageReport))).all()
        assert len(message_reports) == 1
        reports = (await db.scalars(select(Report))).all()
        assert len(reports) == 1
        assert reports[0].target_type == "message"

        own = await client.post(
            "/api/v1/reports",
            json={
                "target_type": "message",
                "target_public_id": str(message.id),
                "reason": "other",
            },
        )
        assert own.status_code == 422
        assert own.json()["error"]["code"] == "self_report"
