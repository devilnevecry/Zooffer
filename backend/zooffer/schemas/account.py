from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatchView(BaseModel):
    """Public-safe representation of a mutual animal match."""

    conversation_public_id: UUID | None = None
    animal_name: str
    animal_public_id: UUID
    listing_slug: str | None = None
    listing_title: str | None = None
    species: str
    breed: str | None = None
    sex: str
    primary_photo_url: str | None = None
    owner_display_name: str | None = None
    created_at: datetime


class MatchListView(BaseModel):
    items: list[MatchView]


class NotificationPreferenceView(BaseModel):
    category: str
    in_app: bool
    telegram: bool
    email: bool
    quiet_from: int | None = None
    quiet_to: int | None = None


class NotificationPreferenceList(BaseModel):
    items: list[NotificationPreferenceView]


class NotificationPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=40)
    in_app: bool = True
    telegram: bool = True
    email: bool = False
    quiet_from: int | None = Field(default=None, ge=0, le=23)
    quiet_to: int | None = Field(default=None, ge=0, le=23)

    @field_validator("category")
    @classmethod
    def known_category(cls, value: str) -> str:
        allowed = {
            "matches",
            "messages",
            "inquiries",
            "listing_moderation",
            "subscriptions",
            "partners",
            "support",
            "security",
        }
        if value not in allowed:
            raise ValueError("Неизвестная категория уведомлений")
        return value


class NotificationPreferenceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NotificationPreferenceUpdate] = Field(min_length=1, max_length=20)


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=10, max_length=5000)
    consent: bool

    @field_validator("subject", "message")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = value.replace("\r\n", "\n").strip()
        if not cleaned:
            raise ValueError("Заполните поле")
        return cleaned

    @field_validator("consent")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Нужно согласие на обработку обращения")
        return value


class SupportTicketView(BaseModel):
    public_id: UUID
    subject: str
    status: str
    created_at: datetime


class PartnerOfferView(BaseModel):
    public_id: UUID
    partner_name: str
    partner_slug: str
    title: str
    description: str
    category: str
    discount_code: str | None = None
    terms: str
    destination_url: str
    is_featured: bool
    erid: str | None = None
    ad_label: str | None = None


class PartnerOfferList(BaseModel):
    items: list[PartnerOfferView]


class PartnerInquiryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    category: str = Field(min_length=2, max_length=24)
    message: str = Field(min_length=10, max_length=3000)
    consent: bool

    @field_validator("email")
    @classmethod
    def email_has_at(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("Укажите корректный e-mail")
        return cleaned

    @field_validator("category")
    @classmethod
    def known_category(cls, value: str) -> str:
        allowed = {"food", "stores", "vet", "grooming", "services"}
        if value not in allowed:
            raise ValueError("Неизвестная категория партнёра")
        return value

    @field_validator("consent")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Нужно согласие на обработку данных")
        return value


class PlanView(BaseModel):
    code: str
    name: str
    description: str
    price_kopecks: int
    currency: str
    stars_amount: int | None = None
    period_days: int
    entitlements: list[str]
    is_placeholder_price: bool


class PlanList(BaseModel):
    items: list[PlanView]


class SubscriptionView(BaseModel):
    status: str
    plan_code: str | None = None
    plan_name: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    entitlements: list[str]
    quota_limit: int
    quota_unlimited: bool
    payments_available: bool
    payments_demo: bool = False
    payment_provider: str = "fake"


class BlockedUserView(BaseModel):
    id: UUID
    display_name: str | None = None
    blocked_at: datetime


class BlockedUserList(BaseModel):
    items: list[BlockedUserView]


class AccountDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(min_length=1, max_length=40)
