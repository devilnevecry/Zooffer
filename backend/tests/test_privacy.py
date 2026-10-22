from __future__ import annotations

import json
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
