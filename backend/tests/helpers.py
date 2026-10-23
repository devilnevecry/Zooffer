from __future__ import annotations

import io
from typing import Any

from httpx import AsyncClient
from PIL import Image

PASSWORD = "Correct horse battery staple"


async def register(
    client: AsyncClient,
    email: str,
    *,
    first_name: str = "Анна",
    last_name: str | None = "Петрова",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "first_name": first_name,
            "last_name": last_name,
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    client.headers["X-CSRF-Token"] = body["csrf_token"]
    return body["user"]


async def login(client: AsyncClient, email: str) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    client.headers["X-CSRF-Token"] = body["csrf_token"]
    return body["user"]


async def create_animal(
    client: AsyncClient,
    *,
    name: str = "Бублик",
    species: str = "dog",
    sex: str = "male",
    birth_date: str | None = "2021-05-10",
    colour: str = "рыжий",
    size: str = "medium",
    has_pedigree: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "species": species,
        "sex": sex,
        "colour": colour,
        "size": size,
        "birth_date": birth_date,
        "has_pedigree": has_pedigree,
        "vaccinated": True,
        "description": "Спокойный и дружелюбный питомец.",
    }
    response = await client.post("/api/v1/animals", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _jpeg_bytes(colour: tuple[int, int, int] = (200, 120, 60)) -> bytes:
    image = Image.new("RGB", (320, 240), colour)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


async def upload_photo(
    client: AsyncClient, animal_public_id: str, *, colour: tuple[int, int, int] = (200, 120, 60)
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/animals/{animal_public_id}/photos",
        files={"file": ("photo.jpg", _jpeg_bytes(colour), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_listing(
    client: AsyncClient,
    animal_public_id: str,
    *,
    purpose: str = "sale",
    title: str = "Щенок ищет новый дом",
    description: str = "Здоровый, привитый, живёт в семье.",
    price_kopecks: int | None = 2500000,
    negotiable: bool = False,
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/listings",
        json={
            "animal_id": animal_public_id,
            "purpose": purpose,
            "title": title,
            "description": description,
            "price_kopecks": price_kopecks,
            "negotiable": negotiable,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


PUBLISH_CONSENTS = {
    "confirm_adult": True,
    "confirm_animal_welfare": True,
    "confirm_photo_rights": True,
    "confirm_no_prohibited": True,
    "confirm_accuracy": True,
}


async def publish_listing(client: AsyncClient, listing_public_id: str) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/listings/{listing_public_id}/publish", json=PUBLISH_CONSENTS
    )
    assert response.status_code == 200, response.text
    return response.json()


async def make_published_listing(
    client: AsyncClient,
    *,
    name: str = "Бублик",
    purpose: str = "sale",
    title: str = "Щенок ищет новый дом",
    description: str = "Здоровый, привитый, живёт в семье.",
    price_kopecks: int | None = 2500000,
    species: str = "dog",
    sex: str = "male",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    animal = await create_animal(client, name=name, species=species, sex=sex)
    await upload_photo(client, animal["public_id"])
    listing = await create_listing(
        client,
        animal["public_id"],
        purpose=purpose,
        title=title,
        description=description,
        price_kopecks=price_kopecks,
    )
    published = await publish_listing(client, listing["public_id"])
    return animal, listing, published


async def swipe(
    client: AsyncClient,
    listing_public_id: str,
    *,
    action: str = "like",
    request_id: str,
    source: str = "web",
) -> Any:
    return await client.post(
        "/api/v1/discovery/swipes",
        json={
            "request_id": request_id,
            "action": action,
            "listing_public_id": listing_public_id,
            "source": source,
        },
    )
