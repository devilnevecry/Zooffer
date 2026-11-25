from __future__ import annotations

import json
from datetime import UTC
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from tests.helpers import make_published_listing, register
from zooffer.db.models import Profile, User, UserPrivateData

FORBIDDEN_KEY_PARTS = {
    "email",
    "phone",
    "telegram",
    "date_of_birth",
    "address",
    "user_id",
    "owner_id",
    "last_active",
    "session",
    "subscription",
    "payment",
    "credential",
    "password",
    "quota",
}


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys |= _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            keys |= _walk_keys(item)
    return keys


def _assert_no_private_keys(payload: Any) -> None:
    for key in _walk_keys(payload):
        lowered = key.lower()
        assert not any(part in lowered for part in FORBIDDEN_KEY_PARTS), key


async def test_public_surfaces_expose_only_allow_listed_owner_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    _, listing, _ = await make_published_listing(client)
    owner_row = await db.scalar(select(User).where(User.public_id == owner["public_id"]))
    assert owner_row is not None
    private = await db.get(UserPrivateData, owner_row.id)
    assert private is not None
    private.phone_encrypted = "+79990001122"
    private.telegram_username_encrypted = "private_owner_handle"
    private.address_encrypted = "Секретный адрес 42"
    await db.commit()

    search = await client.get("/api/v1/public/listings")
    detail = await client.get(f"/api/v1/public/listings/{listing['slug']}")
    home = await client.get("/api/v1/public/home")
    profile = await client.get(f"/api/v1/public/owners/{owner['public_id']}")
    for response in (search, detail, home, profile):
        assert response.status_code == 200, response.text

    for response in (search, detail, home):
        payload = response.json()
        _assert_no_private_keys(payload)
        text = json.dumps(payload, ensure_ascii=False)
        assert "owner@example.com" not in text
        assert "+79990001122" not in text
        assert "private_owner_handle" not in text
        assert "Секретный адрес 42" not in text
        assert str(owner_row.id) not in text
        assert owner["public_id"] not in text

    assert profile.json() == {"display_name": "Анна Петрова"}
    _assert_no_private_keys(profile.json())


async def test_auth_me_shows_private_data_only_to_owner(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == "owner@example.com"
    # Another user's public id is not a substitute for session authentication.
    assert (await client.get(f"/api/v1/public/owners/{body['user']['public_id']}")).json() == {
        "display_name": "Анна Петрова"
    }


async def test_display_name_falls_back_and_never_uses_email(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com", last_name=None)
    owner_row = await db.scalar(select(User).where(User.public_id == owner["public_id"]))
    assert owner_row is not None
    profile = await db.get(Profile, owner_row.id)
    assert profile is not None

    await make_published_listing(client)

    response = await client.get(f"/api/v1/public/owners/{owner['public_id']}")
    assert response.json() == {"display_name": "Анна"}

    profile.public_first_name = None
    profile.public_last_name = None
    await db.commit()
    hidden = await client.get(f"/api/v1/public/owners/{owner['public_id']}")
    assert hidden.json() == {"display_name": None}
    assert "owner@example.com" not in hidden.text


async def test_lost_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    animal_resp = await client.post(
        "/api/v1/animals",
        json={
            "name": "Бублик",
            "species": "dog",
            "sex": "male",
            "colour": "рыжий",
            "size": "medium",
            "birth_date": "2021-05-10",
            "has_pedigree": False,
            "vaccinated": True,
            "description": "Спокойный.",
        },
    )
    assert animal_resp.status_code == 201, animal_resp.text
    animal = animal_resp.json()
    report_resp = await client.post(
        "/api/v1/lost",
        json={
            "animal_id": animal["public_id"],
            "title": "Потерялся Бублик",
            "description": "Убежал в парке.",
            "last_seen_latitude": 55.75,
            "last_seen_longitude": 37.62,
            "radius_km": 5,
        },
    )
    assert report_resp.status_code == 201, report_resp.text
    report = report_resp.json()

    owner_row = await db.scalar(select(User).where(User.public_id == owner["public_id"]))
    assert owner_row is not None
    private = await db.get(UserPrivateData, owner_row.id)
    assert private is not None
    private.phone_encrypted = "+79990001122"
    private.telegram_username_encrypted = "private_owner_handle"
    private.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/lost")
    detail = await client.get(f"/api/v1/lost/{report['public_id']}")
    for response in (listing, detail):
        assert response.status_code == 200, response.text
        payload = response.json()
        _assert_no_private_keys(payload)
        text = json.dumps(payload, ensure_ascii=False)
        assert "owner@example.com" not in text
        assert "+79990001122" not in text
        assert "private_owner_handle" not in text
        assert "Секретный адрес 42" not in text
        assert str(owner_row.id) not in text
        assert owner["public_id"] not in text


async def test_places_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/places",
        json={
            "category": "park",
            "name": "Парк Дружбы",
            "description": "Собаки на поводке.",
            "latitude": 55.75,
            "longitude": 37.62,
        },
    )
    assert resp.status_code == 201, resp.text
    # public list only contains approved places; a freshly created place is pending
    # and must not leak private data when (if) exposed.

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/places")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text
    assert owner["public_id"] not in text


async def test_services_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/services/profiles",
        json={"category": "vet", "title": "Ветеринар Анна", "description": "Выезд на дом."},
    )
    assert resp.status_code == 201, resp.text

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/services/profiles")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text


async def test_organizations_public_surfaces_do_not_leak_private_data(
    client: AsyncClient, db
) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/organizations",
        json={"org_type": "shelter", "name": "Приют Лапа", "description": "Собаки ищут дом."},
    )
    assert resp.status_code == 201, resp.text

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/organizations")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text
    assert owner["public_id"] not in text


async def test_qa_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/qa/questions",
        json={"title": "Как кормить щенка?", "body": "Вопрос по питанию.", "tags": ["dog"]},
    )
    assert resp.status_code == 201, resp.text
    question = resp.json()

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/qa/questions")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text
    assert owner["public_id"] not in text

    detail = await client.get(f"/api/v1/qa/questions/{question['public_id']}")
    assert detail.status_code == 200
    _assert_no_private_keys(detail.json())


async def test_events_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    from datetime import datetime, timedelta

    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/events",
        json={
            "event_type": "meetup",
            "title": "Встреча владельцев",
            "description": "Прогулка в парке.",
            "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text
    event = resp.json()
    pub_id = event["public_id"]

    # publish
    pub = await client.post(f"/api/v1/events/{pub_id}/publish")
    assert pub.status_code == 200

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/events")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text


async def test_stories_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/stories",
        json={"title": "История спасения", "body": "Текст истории.", "tags": ["rescue"]},
    )
    assert resp.status_code == 201, resp.text
    story = resp.json()
    await client.post(f"/api/v1/stories/{story['public_id']}/publish")

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/stories")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text
    assert owner["public_id"] not in text


async def test_channels_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/channels",
        json={"title": "Канал приюта", "description": "Новости."},
    )
    assert resp.status_code == 201, resp.text

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/channels")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text


async def test_market_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    shop_resp = await client.post(
        "/api/v1/market/shops",
        json={"name": "Зоомагазин", "description": "Корм и аксессуары."},
    )
    assert shop_resp.status_code == 201, shop_resp.text
    shop = shop_resp.json()

    # verify shop as admin by elevating
    from sqlalchemy import select

    from zooffer.db.models import Shop
    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    shop_row = await db.scalar(select(Shop).where(Shop.public_id == shop["public_id"]))
    assert shop_row is not None
    shop_row.status = "approved"
    shop_row.verified = True
    owner_row.role = "admin"
    await db.commit()

    product_resp = await client.post(
        "/api/v1/market/products",
        json={
            "shop_id": shop["public_id"],
            "title": "Корм для собак",
            "description": "Премиум.",
            "price_kopecks": 150000,
            "stock": 10,
        },
    )
    assert product_resp.status_code == 201, product_resp.text
    product = product_resp.json()
    await client.post(f"/api/v1/market/products/{product['public_id']}/publish")

    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    for url in ("/api/v1/market/shops", "/api/v1/market/products"):
        listing = await client.get(url)
        assert listing.status_code == 200
        payload = listing.json()
        _assert_no_private_keys(payload)
        text = json.dumps(payload, ensure_ascii=False)
        assert "owner@example.com" not in text
        assert "+79990001122" not in text
        assert "private_owner_handle" not in text
        assert "Секретный адрес 42" not in text
        assert str(owner_row.id) not in text


async def test_videos_public_surfaces_do_not_leak_private_data(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    resp = await client.post(
        "/api/v1/videos",
        json={"caption": "Видео о питомце", "media_key": "videos/ab/cd/full.webp"},
    )
    assert resp.status_code == 201, resp.text

    from zooffer.db.models import User as U

    owner_row = await db.scalar(select(U).where(U.public_id == owner["public_id"]))
    assert owner_row is not None
    private_row = await db.get(UserPrivateData, owner_row.id)
    assert private_row is not None
    private_row.phone_encrypted = "+79990001122"
    private_row.telegram_username_encrypted = "private_owner_handle"
    private_row.address_encrypted = "Секретный адрес 42"
    await db.commit()

    listing = await client.get("/api/v1/videos")
    assert listing.status_code == 200
    payload = listing.json()
    _assert_no_private_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    assert "owner@example.com" not in text
    assert "+79990001122" not in text
    assert "private_owner_handle" not in text
    assert "Секретный адрес 42" not in text
    assert str(owner_row.id) not in text
