from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import (
    create_animal,
    create_listing,
    make_published_listing,
    publish_listing,
    register,
    upload_photo,
)


async def test_animal_photo_listing_lifecycle(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    animal = await create_animal(client)
    photo = await upload_photo(client, animal["public_id"])
    assert photo["is_primary"] is True
    assert photo["width"] > 0 and photo["height"] > 0

    listing = await create_listing(client, animal["public_id"])
    assert listing["status"] == "draft"
    assert listing["slug"]
    assert listing["slug"].startswith("shchenok")

    published = await publish_listing(client, listing["public_id"])
    assert published["status"] == "published"
    assert published["published_at"] is not None
    assert published["expires_at"] is not None

    search = await client.get("/api/v1/public/listings", params={"q": "щенок"})
    assert search.status_code == 200, search.text
    items = search.json()["items"]
    assert [item["public_id"] for item in items] == [listing["public_id"]]
    assert items[0]["owner"] == {"display_name": "Анна Петрова"}
    assert items[0]["primary_photo"]["url"].endswith(".webp")

    detail = await client.get(f"/api/v1/public/listings/{listing['slug']}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["public_id"] == listing["public_id"]
    assert body["animal"]["photos"]
    assert body["owner"]["display_name"] == "Анна Петрова"

    paused = await client.post(f"/api/v1/listings/{listing['public_id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert (await client.get(f"/api/v1/public/listings/{listing['slug']}")).status_code == 404

    renewed = await client.post(f"/api/v1/listings/{listing['public_id']}/renew")
    assert renewed.status_code == 200
    assert renewed.json()["status"] == "published"

    sold = await client.post(f"/api/v1/listings/{listing['public_id']}/sold")
    assert sold.status_code == 200
    assert sold.json()["status"] == "sold"


async def test_publish_requires_photo(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    animal = await create_animal(client)
    listing = await create_listing(client, animal["public_id"])
    response = await client.post(f"/api/v1/listings/{listing['public_id']}/publish")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "photo_required"


async def test_publish_with_contact_details_goes_to_moderation(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    animal = await create_animal(client)
    await upload_photo(client, animal["public_id"])
    listing = await create_listing(
        client,
        animal["public_id"],
        description="Пишите на owner@example.com или в телеграм @secret_owner",
    )
    response = await client.post(f"/api/v1/listings/{listing['public_id']}/publish")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending_moderation"

    search = await client.get("/api/v1/public/listings")
    assert search.json()["items"] == []
    assert (await client.get(f"/api/v1/public/listings/{listing['slug']}")).status_code == 404


async def test_listing_validation_rejects_mass_assignment(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    animal = await create_animal(client)
    response = await client.post(
        "/api/v1/listings",
        json={
            "animal_id": animal["public_id"],
            "purpose": "sale",
            "title": "Щенок в добрые руки",
            "price_kopecks": 100000,
            "status": "published",
            "owner_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 422

    sale_without_price = await client.post(
        "/api/v1/listings",
        json={
            "animal_id": animal["public_id"],
            "purpose": "sale",
            "title": "Щенок в добрые руки",
        },
    )
    assert sale_without_price.status_code == 422

    adoption_with_price = await client.post(
        "/api/v1/listings",
        json={
            "animal_id": animal["public_id"],
            "purpose": "adoption",
            "title": "Отдам щенка в добрые руки",
            "price_kopecks": 100000,
        },
    )
    assert adoption_with_price.status_code == 422


async def test_foreign_listing_and_animal_are_not_accessible(client: AsyncClient) -> None:
    owner = await register(client, "owner@example.com")
    _, listing, _ = await make_published_listing(client)
    animal = await create_animal(client, name="Второй")

    # A different account must not be able to touch the first account's resources.
    await register(client, "other@example.com", first_name="Иван", last_name=None)
    listing_id = listing["public_id"]

    assert (
        await client.patch(f"/api/v1/listings/{listing_id}", json={"title": "Другой заголовок"})
    ).status_code == 404
    assert (await client.post(f"/api/v1/listings/{listing_id}/pause")).status_code == 404
    assert (await client.delete(f"/api/v1/listings/{listing_id}")).status_code == 405
    assert (
        await client.post(
            f"/api/v1/animals/{animal['public_id']}/photos",
            files={"file": ("photo.jpg", b"not an image", "image/jpeg")},
        )
    ).status_code == 404

    owner_public = await client.get(f"/api/v1/public/owners/{owner['public_id']}")
    assert owner_public.status_code == 200
    assert owner_public.json() == {"display_name": "Анна Петрова"}


async def test_upload_attacks_are_rejected(client: AsyncClient) -> None:
    await register(client, "owner@example.com")
    animal = await create_animal(client)
    url = f"/api/v1/animals/{animal['public_id']}/photos"

    text = await client.post(
        url, files={"file": ("evil.jpg", b"<svg>alert(1)</svg>", "image/jpeg")}
    )
    assert text.status_code == 422
    assert text.json()["error"]["code"] == "invalid_image"

    svg = await client.post(
        url,
        files={
            "file": ("evil.svg", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', "image/svg+xml")
        },
    )
    assert svg.status_code == 422

    empty = await client.post(url, files={"file": ("empty.jpg", b"", "image/jpeg")})
    assert empty.status_code == 422


async def test_documents_are_private_and_media_endpoint_is_allow_listed(
    client: AsyncClient,
) -> None:
    await register(client, "owner@example.com")
    animal = await create_animal(client)
    response = await client.post(
        f"/api/v1/animals/{animal['public_id']}/documents",
        files={"file": ("pedigree.pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "private"
    assert "storage_key" not in body
    assert "url" not in body
    assert "documents/" not in response.text

    traversal = await client.get("/api/v1/media/documents%2F..%2Fsecret.pdf")
    assert traversal.status_code == 404
    private = await client.get("/api/v1/media/documents/whatever.pdf")
    assert private.status_code == 404
    missing = await client.get("/api/v1/media/animals/missing.webp")
    assert missing.status_code == 404


async def test_dictionaries_are_public(client: AsyncClient) -> None:
    response = await client.get("/api/v1/public/dictionaries")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"regions", "cities", "breeds"}
