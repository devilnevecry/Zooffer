from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from tests.helpers import (
    create_animal,
    create_listing,
    login,
    make_published_listing,
    publish_listing,
    register,
    swipe,
    upload_photo,
)
from zooffer.db.models import (
    ConversationParticipant,
    DailyQuotaUsage,
    EntitlementGrant,
    Match,
    SystemSetting,
    User,
)
from zooffer.main import app


@asynccontextmanager
async def extra_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


async def test_feed_excludes_own_listings_and_swiped_items(client: AsyncClient) -> None:
    owner = await register(client, "owner@example.com")
    _, owner_listing, _ = await make_published_listing(client, title="Щенок ищет семью")

    async with extra_client() as guest:
        response = await guest.get("/api/v1/discovery/feed")
        assert response.status_code == 200
        body = response.json()
        assert body["guest"] is True
        assert body["quota"]["limit"] == 0
        assert [item["public_id"] for item in body["items"]] == [owner_listing["public_id"]]

    async with extra_client() as other:
        await register(other, "other@example.com", first_name="Иван", last_name=None)
        own_animal = await create_animal(other, name="Своя собака", sex="female")
        await upload_photo(other, own_animal["public_id"])
        own_listing = await create_listing(
            other, own_animal["public_id"], title="Своё объявление", price_kopecks=100000
        )
        await publish_listing(other, own_listing["public_id"])

        feed = await other.get("/api/v1/discovery/feed")
        assert feed.status_code == 200
        ids = [item["public_id"] for item in feed.json()["items"]]
        assert owner_listing["public_id"] in ids
        assert own_listing["public_id"] not in ids
        assert owner["public_id"] not in feed.text

        own_swipe = await swipe(other, own_listing["public_id"], request_id="own-listing-1")
        assert own_swipe.status_code == 422
        assert own_swipe.json()["error"]["code"] == "own_listing"

        liked = await swipe(other, owner_listing["public_id"], request_id="request-0001")
        assert liked.status_code == 200, liked.text
        assert liked.json()["match_created"] is False

        after = await other.get("/api/v1/discovery/feed")
        assert owner_listing["public_id"] not in [
            item["public_id"] for item in after.json()["items"]
        ]


async def test_swipe_idempotency_and_conflicts(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    _, listing, _ = await make_published_listing(client)

    async with extra_client() as other:
        await register(other, "other@example.com", first_name="Иван", last_name=None)

        first = await swipe(other, listing["public_id"], request_id="stable-request-1")
        assert first.status_code == 200, first.text
        remaining = first.json()["remaining"]

        replay = await swipe(other, listing["public_id"], request_id="stable-request-1")
        assert replay.status_code == 200, replay.text
        assert replay.json()["remaining"] == remaining

        conflict = await swipe(
            other, listing["public_id"], action="skip", request_id="different-request-2"
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "swipe_exists"


async def test_quota_is_server_side_and_cannot_be_exceeded(client: AsyncClient, db) -> None:
    await register(client, "owner@example.com")
    animal_one = await create_animal(client, name="Первая собака")
    await upload_photo(client, animal_one["public_id"])
    listing_one = await create_listing(
        client, animal_one["public_id"], title="Первое объявление", price_kopecks=100000
    )
    await publish_listing(client, listing_one["public_id"])
    animal_two = await create_animal(client, name="Вторая собака", sex="female")
    await upload_photo(client, animal_two["public_id"])
    listing_two = await create_listing(
        client, animal_two["public_id"], title="Второе объявление", price_kopecks=100000
    )
    await publish_listing(client, listing_two["public_id"])

    db.add(SystemSetting(key="free_daily_swipes", value={"value": 1}))
    await db.commit()

    async with extra_client() as other:
        user = await register(other, "other@example.com", first_name="Иван", last_name=None)

        first = await swipe(other, listing_one["public_id"], request_id="quota-request-1")
        assert first.status_code == 200, first.text
        assert first.json()["limit"] == 1
        assert first.json()["remaining"] == 0

        blocked = await swipe(other, listing_two["public_id"], request_id="quota-request-2")
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "quota_exceeded"

        quota = await other.get("/api/v1/discovery/quota")
        assert quota.status_code == 200
        assert quota.json()["used"] == 1
        assert quota.json()["limit"] == 1

    used = await db.scalar(
        select(DailyQuotaUsage.used_count).where(
            DailyQuotaUsage.user_id
            == select(User.id).where(User.public_id == UUID(user["public_id"])).scalar_subquery()
        )
    )
    assert used == 1


async def test_undo_requires_entitlement_and_restores_quota(client: AsyncClient, db) -> None:
    await register(client, "owner@example.com")
    _, listing, _ = await make_published_listing(client)

    async with extra_client() as other:
        user = await register(other, "other@example.com", first_name="Иван", last_name=None)
        internal_id = await db.scalar(
            select(User.id).where(User.public_id == UUID(user["public_id"]))
        )
        assert internal_id is not None
        forbidden = await other.post("/api/v1/discovery/undo")
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "entitlement_required"

        liked = await swipe(other, listing["public_id"], request_id="undo-request-1")
        assert liked.status_code == 200
        assert liked.json()["remaining"] == 19

        db.add(EntitlementGrant(user_id=internal_id, code="undo", source="manual"))
        await db.commit()

        undone = await other.post("/api/v1/discovery/undo")
        assert undone.status_code == 200, undone.text
        assert undone.json()["undone"] is True
        assert undone.json()["quota"]["remaining"] == 20

        again = await other.post("/api/v1/discovery/undo")
        assert again.status_code == 404


async def test_mutual_like_creates_match_and_conversation(client: AsyncClient, db) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        _owner = await register(owner_client, "owner@example.com")
        _owner_animal, owner_listing, _ = await make_published_listing(
            owner_client,
            name="Арчи",
            purpose="mating",
            title="Вязка: кобель Арчи",
            price_kopecks=None,
            sex="male",
        )

        _other = await register(other_client, "other@example.com", first_name="Мария")
        other_animal = await create_animal(other_client, name="Лада", species="dog", sex="female")
        await upload_photo(other_client, other_animal["public_id"])
        other_listing = await create_listing(
            other_client,
            other_animal["public_id"],
            purpose="mating",
            title="Вязка: сука Лада",
            price_kopecks=None,
        )
        await publish_listing(other_client, other_listing["public_id"])

        # The other user likes first; no match yet.
        first = await swipe(other_client, owner_listing["public_id"], request_id="match-request-1")
        assert first.status_code == 200, first.text
        assert first.json()["match_created"] is False

        # The owner likes back: mutual match, exactly once.
        back = await swipe(owner_client, other_listing["public_id"], request_id="match-request-2")
        assert back.status_code == 200, back.text
        assert back.json()["match_created"] is True
        assert back.json()["conversation_public_id"]

        replay = await swipe(owner_client, other_listing["public_id"], request_id="match-request-2")
        assert replay.status_code == 200
        assert replay.json()["conversation_public_id"] == back.json()["conversation_public_id"]

    matches = (await db.scalars(select(Match))).all()
    assert len(matches) == 1
    participants = await db.scalar(
        select(func.count())
        .select_from(ConversationParticipant)
        .where(ConversationParticipant.conversation_id == matches[0].conversation_id)
    )
    assert participants == 2
    assert str(matches[0].animal_a_id) != str(matches[0].animal_b_id)


async def test_skip_never_creates_match(client: AsyncClient, db) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        await register(owner_client, "owner@example.com")
        _, owner_listing, _ = await make_published_listing(
            owner_client, purpose="mating", title="Вязка: кобель", price_kopecks=None
        )
        await register(other_client, "other@example.com", first_name="Мария")

        response = await swipe(
            other_client, owner_listing["public_id"], action="skip", request_id="skip-request-1"
        )
        assert response.status_code == 200
        assert response.json()["match_created"] is False

    assert (await db.scalars(select(Match))).all() == []


async def test_favorites_are_owner_scoped(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    _, listing, _ = await make_published_listing(client)
    listing_id = listing["public_id"]

    async with extra_client() as other:
        await register(other, "other@example.com", first_name="Иван", last_name=None)
        added = await other.post(f"/api/v1/favorites/{listing_id}")
        assert added.status_code == 200
        duplicate = await other.post(f"/api/v1/favorites/{listing_id}")
        assert duplicate.status_code == 200

        favorites = await other.get("/api/v1/favorites")
        assert [item["public_id"] for item in favorites.json()["items"]] == [listing_id]

        removed = await other.delete(f"/api/v1/favorites/{listing_id}")
        assert removed.status_code == 200
        assert (await other.get("/api/v1/favorites")).json()["items"] == []

    assert (await client.get("/api/v1/favorites")).json()["items"] == []


async def test_login_returns_to_owner_session(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    async with extra_client() as other:
        await register(other, "other@example.com", first_name="Иван", last_name=None)
        assert (await other.get("/api/v1/auth/me")).json()["user"]["first_name"] == "Иван"
        await login(other, "owner@example.com")
        assert (await other.get("/api/v1/auth/me")).json()["user"]["first_name"] == "Анна"
