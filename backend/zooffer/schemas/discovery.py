from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zooffer.core.enums import SwipeAction, SwipeSource
from zooffer.schemas.public import PublicListingCardView


class SwipeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    action: SwipeAction
    listing_public_id: UUID
    source: SwipeSource = SwipeSource.WEB


class QuotaView(BaseModel):
    limit: int
    used: int
    remaining: int
    resets_at: datetime
    unlimited: bool = False


class SwipeResponse(BaseModel):
    action: SwipeAction
    remaining: int
    limit: int
    resets_at: datetime
    unlimited: bool = False
    match_created: bool = False
    conversation_public_id: UUID | None = None


class UndoResponse(BaseModel):
    undone: bool
    quota_restored: bool
    quota: QuotaView


class DiscoveryFeedResponse(BaseModel):
    items: list[PublicListingCardView]
    next_cursor: str | None = None
    has_more: bool = False
    quota: QuotaView
    guest: bool = False
