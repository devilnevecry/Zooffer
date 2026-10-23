from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient

from tests.helpers import make_published_listing, register
from zooffer.main import app


@asynccontextmanager
async def extra_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


async def _inquiry(
    client: AsyncClient, listing_public_id: str, message: str | None = "Здравствуйте!"
) -> dict:
    response = await client.post(
        "/api/v1/conversations",
        json={"listing_public_id": listing_public_id, "message": message},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_inquiry_conversation_and_messages(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        owner = await register(owner_client, "owner@example.com")
        _, listing, _ = await make_published_listing(owner_client)

        await register(other_client, "other@example.com", first_name="Иван", last_name=None)
        detail = await _inquiry(other_client, listing["public_id"])
        conversation = detail["conversation"]
        assert conversation["conversation_type"] == "inquiry"
        assert conversation["counterpart"] == {"display_name": "Анна Петрова"}
        assert conversation["listing"]["public_id"] == listing["public_id"]
        assert conversation["unread_count"] == 0
        assert len(detail["messages"]) == 1
        assert detail["messages"][0]["mine"] is True

        listing_conversations = await other_client.get("/api/v1/conversations")
        assert listing_conversations.status_code == 200
        assert listing_conversations.json()["items"][0]["public_id"] == conversation["public_id"]

        # The owner sees the other user's public name only.
        owner_view = await owner_client.get(f"/api/v1/conversations/{conversation['public_id']}")
        assert owner_view.status_code == 200, owner_view.text
        owner_summary = owner_view.json()["conversation"]
        assert owner_summary["counterpart"] == {"display_name": "Иван"}
        assert owner_summary["unread_count"] == 1
        assert owner["public_id"] not in owner_view.text
        assert "other@example.com" not in owner_view.text

        reply = await owner_client.post(
            f"/api/v1/conversations/{conversation['public_id']}/messages",
            json={"body": "Здравствуйте! Давайте познакомимся."},
        )
        assert reply.status_code == 201, reply.text
        assert reply.json()["mine"] is True

        for index in range(3):
            sent = await other_client.post(
                f"/api/v1/conversations/{conversation['public_id']}/messages",
                json={"body": f"Сообщение номер {index}"},
            )
            assert sent.status_code == 201, sent.text

        page = await other_client.get(
            f"/api/v1/conversations/{conversation['public_id']}/messages",
            params={"limit": 2},
        )
        assert page.status_code == 200
        assert page.json()["has_more"] is True
        assert page.json()["next_cursor"]
        first_page = page.json()["items"]
        assert [item["body"] for item in first_page] == [
            "Сообщение номер 1",
            "Сообщение номер 2",
        ]

        older = await other_client.get(
            f"/api/v1/conversations/{conversation['public_id']}/messages",
            params={"limit": 10, "cursor": page.json()["next_cursor"]},
        )
        assert older.status_code == 200
        assert [item["body"] for item in older.json()["items"]][-1] == "Сообщение номер 0"
        assert older.json()["has_more"] is False

        read = await other_client.post(f"/api/v1/conversations/{conversation['public_id']}/read")
        assert read.status_code == 200
        assert read.json()["unread_count"] == 0

        duplicate = await other_client.post(
            f"/api/v1/conversations/{conversation['public_id']}/messages",
            json={"body": "Сообщение номер 2"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "duplicate_message"


async def test_third_party_cannot_read_conversation(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        await register(owner_client, "owner@example.com")
        _, listing, _ = await make_published_listing(owner_client)
        await register(other_client, "other@example.com", first_name="Иван")
        detail = await _inquiry(other_client, listing["public_id"])

        async with extra_client() as intruder:
            await register(intruder, "intruder@example.com", first_name="Пётр")
            conversation_id = detail["conversation"]["public_id"]
            assert (
                await intruder.get(f"/api/v1/conversations/{conversation_id}")
            ).status_code == 404
            assert (
                await intruder.post(
                    f"/api/v1/conversations/{conversation_id}/messages",
                    json={"body": "Взлом"},
                )
            ).status_code == 404
            assert (
                await intruder.get(f"/api/v1/conversations/{conversation_id}/messages")
            ).status_code == 404


async def test_inquiry_validation_and_idempotency(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        await register(owner_client, "owner@example.com")
        _, listing, _ = await make_published_listing(owner_client)

        own = await owner_client.post(
            "/api/v1/conversations",
            json={"listing_public_id": listing["public_id"], "message": "Себе"},
        )
        assert own.status_code == 422
        assert own.json()["error"]["code"] == "own_listing"

        await register(other_client, "other@example.com", first_name="Иван")
        first = await _inquiry(other_client, listing["public_id"])
        second = await _inquiry(other_client, listing["public_id"], message=None)
        assert second["conversation"]["public_id"] == first["conversation"]["public_id"]
        assert len((await other_client.get("/api/v1/conversations")).json()["items"]) == 1


async def test_blocking_stops_messages_until_unblocked(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        await register(owner_client, "owner@example.com")
        _, listing, _ = await make_published_listing(owner_client)
        await register(other_client, "other@example.com", first_name="Иван")
        detail = await _inquiry(other_client, listing["public_id"])
        conversation_id = detail["conversation"]["public_id"]

        blocked = await owner_client.post(f"/api/v1/conversations/{conversation_id}/block")
        assert blocked.status_code == 200

        status = await owner_client.get(f"/api/v1/conversations/{conversation_id}")
        assert status.json()["conversation"]["blocked"] is True

        blocked_send = await other_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"body": "Вы здесь?"},
        )
        assert blocked_send.status_code == 403
        assert blocked_send.json()["error"]["code"] == "blocked"

        unblocked = await owner_client.delete(f"/api/v1/conversations/{conversation_id}/block")
        assert unblocked.status_code == 200
        resumed = await other_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"body": "Снова на связи"},
        )
        assert resumed.status_code == 201


async def test_notifications_for_inquiry_and_message(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        await register(owner_client, "owner@example.com")
        _, listing, _ = await make_published_listing(owner_client)
        await register(other_client, "other@example.com", first_name="Иван")
        detail = await _inquiry(other_client, listing["public_id"], message="Есть щенки?")
        conversation_id = detail["conversation"]["public_id"]

        notifications = await owner_client.get("/api/v1/notifications")
        assert notifications.status_code == 200
        body = notifications.json()
        assert body["unread_count"] == 1
        assert body["items"][0]["category"] == "inquiries"
        assert body["items"][0]["data"]["conversation_public_id"] == conversation_id

        await other_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"body": "И ещё вопрос"},
        )
        updated = await owner_client.get("/api/v1/notifications")
        assert updated.json()["unread_count"] == 2

        unread = await owner_client.get("/api/v1/notifications/unread-count")
        assert unread.json()["unread_count"] == 2

        read_all = await owner_client.post("/api/v1/notifications/read-all")
        assert read_all.status_code == 200
        assert read_all.json()["unread_count"] == 0

        notification_id = updated.json()["items"][0]["id"]
        one = await owner_client.post(f"/api/v1/notifications/{notification_id}/read")
        assert one.status_code == 200


async def test_mutual_match_creates_notifications(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        await register(owner_client, "owner@example.com")
        _, owner_listing, _ = await make_published_listing(
            owner_client, purpose="mating", title="Вязка: кобель", price_kopecks=None
        )
        await register(other_client, "other@example.com", first_name="Мария")
        _, other_listing, _ = await make_published_listing(
            other_client,
            name="Лада",
            purpose="mating",
            title="Вязка: сука",
            price_kopecks=None,
            sex="female",
        )
        assert (
            await other_client.post(
                "/api/v1/discovery/swipes",
                json={
                    "request_id": "notify-match-1",
                    "action": "like",
                    "listing_public_id": owner_listing["public_id"],
                },
            )
        ).status_code == 200
        match = await owner_client.post(
            "/api/v1/discovery/swipes",
            json={
                "request_id": "notify-match-2",
                "action": "like",
                "listing_public_id": other_listing["public_id"],
            },
        )
        assert match.status_code == 200
        assert match.json()["match_created"] is True

        for client in (owner_client, other_client):
            notifications = await client.get("/api/v1/notifications")
            categories = [item["category"] for item in notifications.json()["items"]]
            assert "matches" in categories
