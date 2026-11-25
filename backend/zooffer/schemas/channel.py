from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChannelCreateRequest(StrictModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=2000)


class ChannelPostCreateRequest(StrictModel):
    body: str = Field(min_length=1, max_length=8000)


class PublicChannelOwnerView(BaseModel):
    display_name: str | None = None


class PublicChannelView(BaseModel):
    public_id: UUID
    title: str
    description: str
    created_at: datetime
    owner: PublicChannelOwnerView


class ChannelOwnerView(BaseModel):
    public_id: UUID
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class ChannelListResponse(BaseModel):
    items: list[PublicChannelView]
    meta: dict[str, Any] = Field(default_factory=dict)


class ChannelPostView(BaseModel):
    id: UUID
    body: str
    created_at: datetime
    author: PublicChannelOwnerView
