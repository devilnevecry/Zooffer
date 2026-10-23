from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BillingOrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: str = Field(min_length=1, max_length=40)


class BillingOrderView(BaseModel):
    public_id: UUID
    plan_code: str
    provider: str
    status: str
    amount_kopecks: int
    currency: str
    confirmation_url: str | None = None
    demo: bool
    created_at: datetime
    expires_at: datetime | None = None
    paid_at: datetime | None = None


class BillingOrderList(BaseModel):
    items: list[BillingOrderView]


class AdminPaymentEventView(BaseModel):
    provider_event_id: str
    event_type: str
    status: str
    signature_valid: bool
    processed_at: datetime | None = None
    error: str | None = None
    created_at: datetime


class AdminPaymentDetailView(BaseModel):
    order: BillingOrderView
    payment_id: str | None = None
    events: list[AdminPaymentEventView]


class AdminEntitlementGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)
    days: int | None = Field(default=None, ge=1, le=3650)


class AdminEntitlementView(BaseModel):
    code: str
    source: str
    expires_at: datetime | None = None
    created_at: datetime


class AdminRefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=400)


class AdminReconcileView(BaseModel):
    paid_orders: int
    active_subscriptions: int
    paid_without_subscription: int
    subscription_without_payment: int
    refunded_kopecks: int
