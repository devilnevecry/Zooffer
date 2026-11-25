from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VideoCreateRequest(StrictModel):
    caption: str = Field(default="", max_length=2000)
    media_key: str = Field(min_length=3, max_length=500)
    thumb_key: str | None = Field(default=None, max_length=500)


class PublicVideoOwnerView(BaseModel):
    display_name: str | None = None


class PublicVideoView(BaseModel):
    public_id: UUID
    caption: str
    media_key: str
    thumb_key: str | None = None
    status: str
    views: int = 0
    likes: int = 0
    created_at: datetime
    author: PublicVideoOwnerView


class VideoListResponse(BaseModel):
    items: list[PublicVideoView]
    meta: dict[str, Any] = Field(default_factory=dict)
