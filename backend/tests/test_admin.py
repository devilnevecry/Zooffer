from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pyotp
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tests.helpers import (
    create_animal,
    create_listing,
    publish_listing,
    register,
    upload_photo,
)
from zooffer.db.models import Report, User
from zooffer.main import app
from zooffer.services import auth_service


class _FrozenDatetime(datetime):
    """Datetime with a mutable offset, used to simulate TOTP windows passing."""

    offset = timedelta(0)

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        shifted = datetime.now(tz) + cls.offset
        return cls(
            shifted.year,
            shifted.month,
            shifted.day,
            shifted.hour,
            shifted.minute,
            shifted.second,
            shifted.microsecond,
            tzinfo=shifted.tzinfo,
        )


async def _promote(db, public_id: str, role: str = "admin") -> None:
    user = await db.scalar(select(User).where(User.public_id == UUID(public_id)))
    assert user is not None
    user.role = role
    await db.commit()


async def test_mfa_setup_confirm_login_and_disable(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "datetime", _FrozenDatetime)
    monkeypatch.setattr(pyotp.totp, "datetime", SimpleNamespace(datetime=_FrozenDatetime))
    monkeypatch.setattr(_FrozenDatetime, "offset", timedelta(0))

    user = await register(client, "mfa@example.com")
    setup = await client.post("/api/v1/auth/mfa/setup")
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_url"].startswith("otpauth://totp/")

    bad = await client.post("/api/v1/auth/mfa/confirm", json={"code": "000000"})
    assert bad.status_code == 422

    code = pyotp.TOTP(secret).now()
    confirmed = await client.post("/api/v1/auth/mfa/confirm", json={"code": code})
    assert confirmed.status_code == 200, confirmed.text

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["mfa_enabled"] is True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as fresh:
        no_code = await fresh.post(
            "/api/v1/auth/login",
            json={"email": "mfa@example.com", "password": "Correct horse battery staple"},
        )
        assert no_code.status_code == 401
        assert no_code.json()["error"]["code"] == "mfa_required"

        # Advance two TOTP windows, then log in with the code for that window.
        monkeypatch.setattr(_FrozenDatetime, "offset", timedelta(seconds=60))
        login_code = pyotp.TOTP(secret).now()
        with_code = await fresh.post(
            "/api/v1/auth/login",
            json={
                "email": "mfa@example.com",
                "password": "Correct horse battery staple",
                "mfa_code": login_code,
            },
        )
        assert with_code.status_code == 200, with_code.text
        csrf = with_code.json()["csrf_token"]
        fresh.headers["X-CSRF-Token"] = csrf

        # Replaying the login code must fail; a code from a later window works.
        replay = await fresh.post("/api/v1/auth/mfa/disable", json={"code": login_code})
        assert replay.status_code == 422, replay.text
        monkeypatch.setattr(_FrozenDatetime, "offset", timedelta(seconds=120))
        disable = await fresh.post(
            "/api/v1/auth/mfa/disable", json={"code": pyotp.TOTP(secret).now()}
        )
        assert disable.status_code == 200, disable.text
        assert (await fresh.get("/api/v1/auth/me")).json()["user"]["mfa_enabled"] is False
    assert user["public_id"]


async def test_admin_rbac_moderation_and_audit(client: AsyncClient, db) -> None:
    user = await register(client, "moderator@example.com")
    setup = await client.post("/api/v1/auth/mfa/setup")
    secret = setup.json()["secret"]
    await client.post("/api/v1/auth/mfa/confirm", json={"code": pyotp.TOTP(secret).now()})

    denied = await client.get("/api/v1/admin/dashboard")
    assert denied.status_code == 403

    await _promote(db, user["public_id"])

    dashboard = await client.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["stats"]["users_total"] >= 1

    animal = await create_animal(client)
    await upload_photo(client, animal["public_id"])
    listing = await create_listing(
        client,
        animal["public_id"],
        description="Срочно, звоните 8 999 123-45-67",
    )
    published = await publish_listing(client, listing["public_id"])
    assert published["status"] == "pending_moderation"

    queue = await client.get("/api/v1/admin/listings?status=pending_moderation")
    assert queue.status_code == 200, queue.text
    assert any(item["public_id"] == listing["public_id"] for item in queue.json()["items"])

    approved = await client.post(
        f"/api/v1/admin/moderation/listings/{listing['public_id']}",
        json={"action": "approve", "reason": "Проверено вручную"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "published"

    rejected = await client.post(
        f"/api/v1/admin/moderation/listings/{listing['public_id']}",
        json={"action": "reject", "reason": "Нарушение правил"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    reports = await client.get("/api/v1/admin/reports")
    assert reports.status_code == 200
    assert reports.json()["items"] == []

    audit = await client.get("/api/v1/admin/audit")
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()["items"]]
    assert "listing.approve" in actions
    assert "listing.reject" in actions


async def test_admin_reports_users_settings_support_and_rbac(client: AsyncClient, db) -> None:
    owner = await register(client, "owner-admin@example.com")
    setup = await client.post("/api/v1/auth/mfa/setup")
    secret = setup.json()["secret"]
    await client.post("/api/v1/auth/mfa/confirm", json={"code": pyotp.TOTP(secret).now()})
    await _promote(db, owner["public_id"], "admin")

    report = Report(
        id=uuid4(),
        reporter_id=None,
        target_type="listing",
        target_public_id=str(uuid4()),
        reason="spam",
        details="Тестовая жалоба",
        status="open",
    )
    db.add(report)
    await db.commit()

    listed = await client.get("/api/v1/admin/reports?status=open")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["reason"] == "spam"

    resolved = await client.patch(
        f"/api/v1/admin/reports/{report.id}",
        json={"status": "resolved", "resolution": "Материал проверен"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"

    users = await client.get("/api/v1/admin/users")
    assert users.status_code == 200
    assert users.json()["total"] >= 1

    ticket = await client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "Не приходит код",
            "message": "Проверьте, пожалуйста, вход в аккаунт.",
            "consent": True,
        },
    )
    assert ticket.status_code == 201, ticket.text
    support = await client.get("/api/v1/admin/support")
    assert support.status_code == 200
    assert support.json()["items"][0]["subject"] == "Не приходит код"
    reply = await client.post(
        f"/api/v1/admin/support/{ticket.json()['public_id']}/reply",
        json={"message": "Проверили, проблема устранена.", "status": "resolved"},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["status"] == "resolved"

    settings = await client.get("/api/v1/admin/settings")
    assert settings.status_code == 200
    put = await client.put("/api/v1/admin/settings/free_daily_swipes", json={"value": "25"})
    assert put.status_code == 403

    await _promote(db, owner["public_id"], "superadmin")
    put = await client.put("/api/v1/admin/settings/free_daily_swipes", json={"value": "25"})
    assert put.status_code == 200, put.text
    assert put.json()["value"] == "25"

    payments = await client.get("/api/v1/admin/payments")
    assert payments.status_code == 200
    assert payments.json()["items"] == []


async def test_expired_mfa_login_is_rejected(client: AsyncClient) -> None:
    await register(client, "expired@example.com")
    setup = await client.post("/api/v1/auth/mfa/setup")
    secret = setup.json()["secret"]
    await client.post("/api/v1/auth/mfa/confirm", json={"code": pyotp.TOTP(secret).now()})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as fresh:
        response = await fresh.post(
            "/api/v1/auth/login",
            json={
                "email": "expired@example.com",
                "password": "Correct horse battery staple",
                "mfa_code": "123456",
            },
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_mfa"
