from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import register


async def test_places_crud_and_radius(client: AsyncClient, db) -> None:
    await register(client, "owner@example.com")
    create = await client.post(
        "/api/v1/places",
        json={
            "category": "park",
            "name": "Парк Дружбы",
            "description": "Собаки на поводке.",
            "latitude": 55.75,
            "longitude": 37.62,
        },
    )
    assert create.status_code == 201, create.text
    place = create.json()
    assert place["status"] == "pending"

    public = await client.get("/api/v1/places")
    assert public.status_code == 200
    assert len(public.json()["items"]) == 0

    import uuid

    from sqlalchemy import select

    from zooffer.db.models import User
    from zooffer.db.models.place import Place

    owner_row = await db.scalar(
        select(User).where(User.public_id == (await _owner_public_id(client)))
    )
    assert owner_row is not None

    approved = Place(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        reporter_id=owner_row.id,
        category="cafe",
        status="approved",
        name="Кафе Лапа",
        description="Можно с собакой.",
        latitude=55.76,
        longitude=37.62,
    )
    db.add(approved)
    await db.commit()

    near = await client.get(
        "/api/v1/places", params={"latitude": 55.75, "longitude": 37.62, "radius_km": 5}
    )
    assert near.status_code == 200
    assert len(near.json()["items"]) >= 1

    far = await client.get("/api/v1/places", params={"latitude": 0, "longitude": 0, "radius_km": 5})
    assert far.status_code == 200
    assert len(far.json()["items"]) == 0


async def _owner_public_id(client: AsyncClient) -> str:
    me = await client.get("/api/v1/auth/me")
    return me.json()["user"]["public_id"]
