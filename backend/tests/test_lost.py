from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import register


async def test_lost_crud_radius_and_sighting(client: AsyncClient, db) -> None:
    await register(client, "owner@example.com")
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
    assert animal_resp.status_code == 201
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
    assert report["status"] == "searching"

    # radius filtering: nearby point returns it
    near = await client.get(
        "/api/v1/lost", params={"latitude": 55.76, "longitude": 37.62, "radius_km": 10}
    )
    assert near.status_code == 200
    assert len(near.json()["items"]) == 1

    far = await client.get("/api/v1/lost", params={"latitude": 0, "longitude": 0, "radius_km": 10})
    assert far.status_code == 200
    assert len(far.json()["items"]) == 0

    # sighting idempotency
    s1 = await client.post(
        f"/api/v1/lost/{report['public_id']}/sightings",
        json={"latitude": 55.7, "longitude": 37.6, "request_id": "r1"},
    )
    assert s1.status_code == 201
    s2 = await client.post(
        f"/api/v1/lost/{report['public_id']}/sightings",
        json={"latitude": 55.7, "longitude": 37.6, "request_id": "r1"},
    )
    assert s2.status_code == 201
    assert s2.json()["idempotent"] is True
    assert s1.json()["id"] == s2.json()["id"]

    # close
    closed = await client.post(f"/api/v1/lost/{report['public_id']}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    # sighting after close fails
    s3 = await client.post(
        f"/api/v1/lost/{report['public_id']}/sightings",
        json={"latitude": 55.7, "longitude": 37.6},
    )
    assert s3.status_code in (400, 422)
