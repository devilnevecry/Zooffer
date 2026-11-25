from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import register


async def test_services_profile_and_review(client: AsyncClient, db) -> None:
    await register(client, "owner@example.com")
    create = await client.post(
        "/api/v1/services/profiles",
        json={"category": "vet", "title": "Ветеринар Анна", "description": "Выезд на дом."},
    )
    assert create.status_code == 201, create.text
    profile = create.json()
    assert profile["status"] == "pending"

    # Make profile approved directly for review flow
    from sqlalchemy import select

    from zooffer.db.models.service import ServiceProfile

    row = await db.scalar(
        select(ServiceProfile).where(ServiceProfile.public_id == profile["public_id"])
    )
    assert row is not None
    row.status = "approved"
    row.verified = True
    await db.commit()

    # review by same user; duplicate should be rejected
    review = await client.post(
        f"/api/v1/services/profiles/{profile['public_id']}/reviews",
        json={"rating": 5, "body": "Отлично!"},
    )
    assert review.status_code == 201, review.text

    listed = await client.get(f"/api/v1/services/profiles/{profile['public_id']}/reviews")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    # duplicate review rejected
    dup = await client.post(
        f"/api/v1/services/profiles/{profile['public_id']}/reviews",
        json={"rating": 4, "body": "Ещё раз"},
    )
    assert dup.status_code in (400, 409, 422)
