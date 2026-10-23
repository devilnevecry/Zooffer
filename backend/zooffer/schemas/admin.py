from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminStatsView(BaseModel):
    users_total: int
    users_new_week: int
    listings_published: int
    listings_pending: int
    reports_open: int
    support_open: int
    subscriptions_active: int
    revenue_kopecks_30d: int
    swipes_today: int
    matches_total: int


class AdminRecentItem(BaseModel):
    created_at: datetime
    action: str
    object_type: str
    object_id: str | None = None
    actor_role: str | None = None


class AdminDashboardView(BaseModel):
    stats: AdminStatsView
    recent_actions: list[AdminRecentItem]


class AdminListingView(BaseModel):
    public_id: UUID
    slug: str
    title: str
    purpose: str
    status: str
    price_kopecks: int | None
    owner_name: str | None
    owner_public_id: UUID
    animal_name: str
    species: str
    city_name: str | None
    photo_url: str | None
    moderation_reason: str | None
    quality_score: int
    created_at: datetime
    published_at: datetime | None


class AdminListingList(BaseModel):
    items: list[AdminListingView]
    total: int


class ModerationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Укажите причину решения")
        return cleaned


class AdminReportView(BaseModel):
    id: UUID
    target_type: str
    target_public_id: str
    reason: str
    details: str | None
    status: str
    reporter_name: str | None
    created_at: datetime
    resolved_at: datetime | None


class AdminReportList(BaseModel):
    items: list[AdminReportView]


class ReportResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern="^(resolved|dismissed|in_review)$")
    resolution: str = Field(min_length=3, max_length=1000)


class AdminUserView(BaseModel):
    public_id: UUID
    display_name: str | None
    email: str | None
    role: str
    status: str
    city_name: str | None
    listings_count: int
    created_at: datetime
    mfa_enabled: bool


class AdminUserList(BaseModel):
    items: list[AdminUserView]
    total: int


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = Field(default=None, pattern="^(user|moderator|admin|superadmin)$")
    status: str | None = Field(default=None, pattern="^(active|suspended|deleted)$")


class AdminSupportTicketView(BaseModel):
    public_id: UUID
    subject: str
    status: str
    channel: str
    user_name: str | None
    last_message: str | None
    created_at: datetime
    updated_at: datetime


class AdminSupportList(BaseModel):
    items: list[AdminSupportTicketView]


class AdminSupportReplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="open", pattern="^(open|pending|resolved|closed)$")


class AdminSettingView(BaseModel):
    key: str
    value: str
    updated_at: datetime | None = None


class AdminSettingsView(BaseModel):
    items: list[AdminSettingView]


class AdminSettingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1, max_length=2000)


class AdminAuditView(BaseModel):
    id: UUID
    action: str
    object_type: str
    object_id: str | None
    actor_role: str | None
    metadata: dict[str, object] | None
    created_at: datetime


class AdminAuditList(BaseModel):
    items: list[AdminAuditView]


class AdminPaymentView(BaseModel):
    public_id: UUID
    user_name: str | None
    plan_code: str
    provider: str
    status: str
    amount_kopecks: int
    currency: str
    created_at: datetime
    paid_at: datetime | None


class AdminPaymentList(BaseModel):
    items: list[AdminPaymentView]
