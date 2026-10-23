from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from tests.helpers import make_published_listing, register
from zooffer.core.security import decrypt_value
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    AuditLog,
    Block,
    Listing,
    Partner,
    PartnerClick,
    PartnerInquiry,
    PartnerOffer,
    Plan,
    Profile,
    Subscription,
    SupportMessage,
    SupportTicket,
    User,
    UserPrivateData,
)
from zooffer.main import app


@asynccontextmanager
async def extra_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


async def _internal_id(db, public_id: str) -> UUID:
    value = await db.scalar(select(User.id).where(User.public_id == UUID(public_id)))
    assert value is not None
    return value


async def _add_partner_offer(
    db,
    *,
    slug: str = "pet-food",
    partner_status: str = "active",
    offer_status: str = "active",
    destination_url: str = "https://example.com/zooffer",
    starts_at=None,
    ends_at=None,
) -> tuple[Partner, PartnerOffer]:
    partner = Partner(
        id=uuid4(),
        name="Корм для питомцев",
        slug=slug,
        description="Партнёр Zooffer",
        status=partner_status,
    )
    offer = PartnerOffer(
        id=uuid4(),
        partner_id=partner.id,
        title="Скидка 15% на первый заказ",
        description="Промокод для владельцев животных",
        category="food",
        discount_code="ZOO15",
        destination_url=destination_url,
        terms="Действует 30 дней",
        starts_at=starts_at,
        ends_at=ends_at,
        status=offer_status,
        is_featured=True,
        erid="ERID-TEST",
        ad_label="Реклама",
        sort_order=1,
    )
    db.add_all([partner, offer])
    await db.commit()
    return partner, offer


async def test_notification_preferences_defaults_and_update(client: AsyncClient) -> None:
    await register(client, "owner@example.com")

    defaults = await client.get("/api/v1/notification-preferences")
    assert defaults.status_code == 200, defaults.text
    items = {item["category"]: item for item in defaults.json()["items"]}
    assert list(items) == [
        "matches",
        "messages",
        "inquiries",
        "listing_moderation",
        "subscriptions",
        "partners",
        "support",
        "security",
    ]
    assert items["matches"]["in_app"] is True
    assert items["matches"]["telegram"] is True
    assert items["matches"]["email"] is False
    assert items["partners"]["telegram"] is False

    updated = await client.put(
        "/api/v1/notification-preferences",
        json={
            "items": [
                {
                    "category": "messages",
                    "in_app": False,
                    "telegram": True,
                    "email": True,
                    "quiet_from": 22,
                    "quiet_to": 7,
                },
                {
                    "category": "partners",
                    "in_app": True,
                    "telegram": True,
                    "email": False,
                },
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    refreshed = {item["category"]: item for item in updated.json()["items"]}
    assert refreshed["messages"] == {
        "category": "messages",
        "in_app": False,
        "telegram": True,
        "email": True,
        "quiet_from": 22,
        "quiet_to": 7,
    }
    assert refreshed["partners"]["telegram"] is True

    unknown = await client.put(
        "/api/v1/notification-preferences",
        json={"items": [{"category": "marketing"}]},
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "validation_error"

    invalid_hour = await client.put(
        "/api/v1/notification-preferences",
        json={"items": [{"category": "matches", "quiet_from": 24}]},
    )
    assert invalid_hour.status_code == 422

    forbidden_field = await client.put(
        "/api/v1/notification-preferences",
        json={"items": [{"category": "matches", "sms": True}]},
    )
    assert forbidden_field.status_code == 422


async def test_support_ticket_validation_and_rate_limit(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    owner_id = await _internal_id(db, owner["public_id"])

    missing_consent = await client.post(
        "/api/v1/support/tickets",
        json={"subject": "Проблема", "message": "Не приходит письмо", "consent": False},
    )
    assert missing_consent.status_code == 422
    assert missing_consent.json()["error"]["code"] == "validation_error"

    short_message = await client.post(
        "/api/v1/support/tickets",
        json={"subject": "Проблема", "message": "Коротко", "consent": True},
    )
    assert short_message.status_code == 422

    created = await client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "  Не приходит письмо  ",
            "message": "  Проверьте, пожалуйста, доставку писем.  ",
            "consent": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["subject"] == "Не приходит письмо"
    assert body["status"] == "open"
    assert UUID(body["public_id"])

    db.expire_all()
    ticket = await db.scalar(
        select(SupportTicket).where(SupportTicket.public_id == UUID(body["public_id"]))
    )
    assert ticket is not None
    assert ticket.user_id == owner_id
    assert ticket.channel == "web"
    message = await db.scalar(
        select(SupportMessage).where(SupportMessage.ticket_id == ticket.id)
    )
    assert message is not None
    assert message.body == "Проверьте, пожалуйста, доставку писем."
    assert message.is_staff is False

    # Five tickets per hour is the documented limit; the sixth is rejected.
    for index in range(4):
        allowed = await client.post(
            "/api/v1/support/tickets",
            json={
                "subject": f"Обращение {index}",
                "message": "Достаточно длинное описание вопроса.",
                "consent": True,
            },
        )
        assert allowed.status_code == 201, allowed.text
    limited = await client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "Ещё одно обращение",
            "message": "Достаточно длинное описание вопроса.",
            "consent": True,
        },
    )
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"


async def test_public_plans_and_partners(client: AsyncClient, db) -> None:
    db.add_all(
        [
            Plan(
                id=uuid4(),
                code="free",
                name="Базовый",
                description="Бесплатный доступ",
                price_kopecks=0,
                currency="RUB",
                stars_amount=None,
                period_days=30,
                entitlements=[],
                is_active=False,
                sort_order=0,
                is_placeholder_price=False,
            ),
            Plan(
                id=uuid4(),
                code="plus",
                name="Zooffer Плюс",
                description="Больше показов и отмена свайпа",
                price_kopecks=39900,
                currency="RUB",
                stars_amount=250,
                period_days=30,
                entitlements=["unlimited_swipes", "undo"],
                is_active=True,
                sort_order=1,
                is_placeholder_price=True,
            ),
        ]
    )
    await _add_partner_offer(db, slug="active-partner")
    await _add_partner_offer(
        db,
        slug="draft-partner",
        partner_status="draft",
    )
    await _add_partner_offer(
        db,
        slug="ended-offer",
        ends_at=utcnow() - timedelta(days=1),
    )
    await _add_partner_offer(
        db,
        slug="future-offer",
        starts_at=utcnow() + timedelta(days=2),
    )
    await db.commit()

    plans = await client.get("/api/v1/public/plans")
    assert plans.status_code == 200, plans.text
    assert [item["code"] for item in plans.json()["items"]] == ["plus"]
    plan = plans.json()["items"][0]
    assert plan["entitlements"] == ["unlimited_swipes", "undo"]
    assert plan["is_placeholder_price"] is True

    offers = await client.get("/api/v1/public/partners")
    assert offers.status_code == 200, offers.text
    items = offers.json()["items"]
    assert [item["partner_slug"] for item in items] == ["active-partner"]
    assert items[0]["discount_code"] == "ZOO15"
    assert items[0]["erid"] == "ERID-TEST"
    assert items[0]["ad_label"] == "Реклама"
    assert items[0]["destination_url"] == "https://example.com/zooffer"
    assert "draft-partner" not in offers.text
    assert "ended-offer" not in offers.text
    assert "future-offer" not in offers.text


async def test_partner_inquiry_stores_encrypted_contact(client: AsyncClient, db) -> None:
    payload = {
        "company": "ООО Зоотовары",
        "contact_name": "Мария",
        "email": " Partner@Example.COM ",
        "phone": "+7 999 000-00-00",
        "category": "food",
        "message": "Хотим разместить предложение для владельцев животных.",
        "consent": True,
    }
    created = await client.post("/api/v1/public/partner-inquiries", json=payload)
    assert created.status_code == 201, created.text
    assert created.json() == {"ok": True}

    db.expire_all()
    inquiry = await db.scalar(select(PartnerInquiry))
    assert inquiry is not None
    assert inquiry.company == "ООО Зоотовары"
    assert inquiry.status == "new"
    assert inquiry.consent_at is not None

    # The ORM decrypts EncryptedText columns, so inspect raw storage to prove encryption.
    raw = (
        await db.execute(text("SELECT email_encrypted, phone_encrypted FROM partner_inquiries"))
    ).one()
    assert "partner@example.com" not in raw.email_encrypted
    assert "+7 999 000-00-00" not in raw.phone_encrypted
    assert decrypt_value(raw.email_encrypted) == "partner@example.com"
    assert decrypt_value(raw.phone_encrypted) == "+7 999 000-00-00"

    invalid_email = await client.post(
        "/api/v1/public/partner-inquiries",
        json={**payload, "email": "not-an-email"},
    )
    assert invalid_email.status_code == 422

    invalid_category = await client.post(
        "/api/v1/public/partner-inquiries",
        json={**payload, "category": "crypto"},
    )
    assert invalid_category.status_code == 422

    missing_consent = await client.post(
        "/api/v1/public/partner-inquiries",
        json={**payload, "consent": False},
    )
    assert missing_consent.status_code == 422

    # Three inquiries per e-mail address per day.
    for _ in range(2):
        allowed = await client.post("/api/v1/public/partner-inquiries", json=payload)
        assert allowed.status_code == 201, allowed.text
    limited = await client.post("/api/v1/public/partner-inquiries", json=payload)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"


async def test_partner_click_redirect_and_tracking(client: AsyncClient, db) -> None:
    _, offer = await _add_partner_offer(db)

    async with extra_client() as guest:
        guest_click = await guest.get(
            f"/go/{offer.id}",
            follow_redirects=False,
            headers={"User-Agent": "ZoofferTest/1.0"},
        )
    assert guest_click.status_code == 302
    assert guest_click.headers["location"] == "https://example.com/zooffer"

    owner = await register(client, "owner@example.com")
    owner_id = await _internal_id(db, owner["public_id"])

    first = await db.scalar(select(PartnerClick).order_by(PartnerClick.created_at))
    assert first is not None
    assert first.offer_id == offer.id
    assert first.user_id is None
    assert first.ip_hash is not None
    assert first.ua_hash is not None
    assert first.attribution_token

    user_click = await client.get(f"/go/{offer.id}", follow_redirects=False)
    assert user_click.status_code == 302
    db.expire_all()
    clicks = list((await db.scalars(select(PartnerClick))).all())
    assert len(clicks) == 2
    assert {click.user_id for click in clicks} == {None, owner_id}

    unknown = await client.get(f"/go/{uuid4()}", follow_redirects=False)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "partner_offer_not_found"

    unsafe_partner, unsafe_offer = await _add_partner_offer(
        db,
        slug="unsafe-partner",
        destination_url="javascript:alert(1)",
    )
    unsafe = await client.get(f"/go/{unsafe_offer.id}", follow_redirects=False)
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["code"] == "invalid_destination"
    assert unsafe_partner.status == "active"


async def test_matches_list_is_private_and_complete(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        owner = await register(owner_client, "owner@example.com")
        _, owner_listing, _ = await make_published_listing(
            owner_client,
            name="Арчи",
            purpose="mating",
            title="Вязка: кобель Арчи",
            price_kopecks=None,
            sex="male",
        )
        other = await register(
            other_client, "other@example.com", first_name="Мария", last_name=None
        )
        _, other_listing, _ = await make_published_listing(
            other_client,
            name="Лада",
            purpose="mating",
            title="Вязка: сука Лада",
            price_kopecks=None,
            sex="female",
        )

        await other_client.post(
            "/api/v1/discovery/swipes",
            json={
                "request_id": "account-match-1",
                "action": "like",
                "listing_public_id": owner_listing["public_id"],
            },
        )
        mutual = await owner_client.post(
            "/api/v1/discovery/swipes",
            json={
                "request_id": "account-match-2",
                "action": "like",
                "listing_public_id": other_listing["public_id"],
            },
        )
        assert mutual.status_code == 200, mutual.text
        assert mutual.json()["match_created"] is True
        conversation_id = mutual.json()["conversation_public_id"]

        owner_matches = await owner_client.get("/api/v1/matches")
        assert owner_matches.status_code == 200, owner_matches.text
        owner_items = owner_matches.json()["items"]
        assert len(owner_items) == 1
        assert owner_items[0]["animal_name"] == "Лада"
        assert owner_items[0]["owner_display_name"] == "Мария"
        assert owner_items[0]["conversation_public_id"] == conversation_id
        assert owner_items[0]["listing_slug"]
        assert owner_items[0]["primary_photo_url"]
        assert other["public_id"] not in owner_matches.text
        assert "other@example.com" not in owner_matches.text

        other_matches = await other_client.get("/api/v1/matches")
        assert other_matches.status_code == 200
        assert other_matches.json()["items"][0]["animal_name"] == "Арчи"
        assert other_matches.json()["items"][0]["owner_display_name"] == "Анна Петрова"
        assert owner["public_id"] not in other_matches.text
        assert "owner@example.com" not in other_matches.text


async def test_account_export_is_owner_scoped(client: AsyncClient) -> None:
    async with extra_client() as owner_client, extra_client() as other_client:
        owner = await register(owner_client, "owner@example.com")
        animal, listing, _ = await make_published_listing(owner_client)
        other = await register(
            other_client, "other@example.com", first_name="Иван", last_name=None
        )
        _, other_listing, _ = await make_published_listing(
            other_client,
            name="Лада",
            title="Собака ищет дом",
            species="dog",
            sex="female",
        )
        await other_client.post(
            "/api/v1/conversations",
            json={"listing_public_id": listing["public_id"], "message": "Здравствуйте!"},
        )
        assert (
            await owner_client.post(f"/api/v1/favorites/{other_listing['public_id']}")
        ).status_code == 200

        response = await owner_client.get("/api/v1/account/export")
        assert response.status_code == 200, response.text
        assert "attachment" in response.headers["content-disposition"]
        assert owner["public_id"] in response.headers["content-disposition"]
        archive = response.json()

        assert archive["format"] == "zooffer-account-export"
        assert archive["version"] == 1
        assert archive["account"]["public_id"] == owner["public_id"]
        assert archive["profile"]["first_name"] == "Анна"
        assert archive["profile"]["last_name"] == "Петрова"
        assert archive["private_data"]["email"] == "owner@example.com"
        assert [item["public_id"] for item in archive["animals"]] == [animal["public_id"]]
        assert [item["public_id"] for item in archive["listings"]] == [listing["public_id"]]
        assert [item["listing_public_id"] for item in archive["favorites"]] == [
            other_listing["public_id"]
        ]
        assert archive["conversations"][0]["counterpart_display_name"] == "Иван"
        assert archive["conversations"][0]["messages"][0]["body"] == "Здравствуйте!"
        assert archive["conversations"][0]["messages"][0]["mine"] is False

        text = response.text.lower()
        assert "password_hash" not in text
        assert "telegram_username_encrypted" not in text
        assert "other@example.com" not in text
        assert other["public_id"] not in response.text

        other_export = await other_client.get("/api/v1/account/export")
        assert other_export.status_code == 200
        assert other_export.json()["private_data"]["email"] == "other@example.com"
        assert owner["public_id"] not in other_export.text


async def test_account_delete_requires_confirmation_and_erases(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    owner_id = await _internal_id(db, owner["public_id"])
    _, _, published = await make_published_listing(client)

    wrong = await client.request(
        "DELETE", "/api/v1/account", json={"confirmation": "удалить всё"}
    )
    assert wrong.status_code == 422
    assert wrong.json()["error"]["code"] == "confirmation_failed"
    assert (await client.get("/api/v1/auth/me")).status_code == 200

    deleted = await client.request(
        "DELETE", "/api/v1/account", json={"confirmation": "удалить"}
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["ok"] is True
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    db.expire_all()
    user = await db.get(User, owner_id)
    assert user is not None
    assert user.status == "deleted"
    assert user.deleted_at is not None

    profile = await db.get(Profile, owner_id)
    assert profile is not None
    assert profile.public_first_name is None
    assert profile.public_last_name is None

    private = await db.get(UserPrivateData, owner_id)
    assert private is not None
    assert private.email_encrypted is None
    assert private.email_hash is None

    listing = await db.scalar(
        select(Listing).where(Listing.public_id == UUID(published["public_id"]))
    )
    assert listing is not None
    assert listing.status == "archived"

    audit = await db.scalar(select(AuditLog).where(AuditLog.action == "account.deleted"))
    assert audit is not None
    assert audit.object_id == owner["public_id"]

    async with extra_client() as login_attempt:
        response = await login_attempt.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Correct horse battery staple"},
        )
        assert response.status_code == 401


async def test_blocked_users_list_and_unblock(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    async with extra_client() as blocked_client, extra_client() as intruder_client:
        blocked = await register(
            blocked_client, "blocked@example.com", first_name="Иван", last_name=None
        )
        await register(intruder_client, "intruder@example.com", first_name="Пётр")

        owner_id = await _internal_id(db, owner["public_id"])
        blocked_id = await _internal_id(db, blocked["public_id"])
        block_id = uuid4()
        db.add(
            Block(
                id=block_id,
                blocker_id=owner_id,
                blocked_id=blocked_id,
                reason="Нежелательные сообщения",
            )
        )
        await db.commit()

        listed = await client.get("/api/v1/blocked-users")
        assert listed.status_code == 200, listed.text
        items = listed.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == str(block_id)
        assert items[0]["display_name"] == "Иван"
        assert blocked["public_id"] not in listed.text

        foreign = await intruder_client.delete(f"/api/v1/blocked-users/{block_id}")
        assert foreign.status_code == 422
        assert foreign.json()["error"]["code"] == "block_not_found"

        missing = await client.delete(f"/api/v1/blocked-users/{uuid4()}")
        assert missing.status_code == 422
        assert missing.json()["error"]["code"] == "block_not_found"

        unblocked = await client.delete(f"/api/v1/blocked-users/{block_id}")
        assert unblocked.status_code == 200
        assert unblocked.json()["ok"] is True
        assert (await client.get("/api/v1/blocked-users")).json()["items"] == []

        db.expire_all()
        assert await db.get(Block, block_id) is None


async def test_subscription_state_and_cancel(client: AsyncClient, db) -> None:
    owner = await register(client, "owner@example.com")
    owner_id = await _internal_id(db, owner["public_id"])

    empty = await client.get("/api/v1/billing/subscription")
    assert empty.status_code == 200, empty.text
    assert empty.json()["status"] == "none"
    assert empty.json()["entitlements"] == []
    assert empty.json()["payments_available"] is True
    assert empty.json()["payments_demo"] is True

    plan = Plan(
        id=uuid4(),
        code="plus",
        name="Zooffer Плюс",
        description="Больше показов",
        price_kopecks=39900,
        currency="RUB",
        period_days=30,
        entitlements=["unlimited_swipes", "undo"],
        is_active=True,
        is_placeholder_price=True,
    )
    subscription_id = uuid4()
    db.add_all(
        [
            plan,
            Subscription(
                id=subscription_id,
                user_id=owner_id,
                plan_id=plan.id,
                status="active",
                provider="fake",
                current_period_start=utcnow() - timedelta(days=1),
                current_period_end=utcnow() + timedelta(days=29),
            ),
        ]
    )
    await db.commit()

    current = await client.get("/api/v1/billing/subscription")
    assert current.status_code == 200, current.text
    body = current.json()
    assert body["status"] == "active"
    assert body["plan_code"] == "plus"
    assert body["plan_name"] == "Zooffer Плюс"
    assert body["cancel_at_period_end"] is False
    assert body["entitlements"] == ["undo", "unlimited_swipes"]
    assert body["quota_unlimited"] is True
    assert body["payments_available"] is True

    async with extra_client() as other_client:
        await register(other_client, "other@example.com")
        none_to_cancel = await other_client.post("/api/v1/billing/cancel")
        assert none_to_cancel.status_code == 422
        assert none_to_cancel.json()["error"]["code"] == "subscription_not_found"

    canceled = await client.post("/api/v1/billing/cancel")
    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["cancel_at_period_end"] is True
    assert canceled.json()["status"] == "active"

    db.expire_all()
    stored = await db.get(Subscription, subscription_id)
    assert stored is not None
    assert stored.cancel_at_period_end is True
    assert stored.canceled_at is not None
