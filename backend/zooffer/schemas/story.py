from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoryCreateRequest(StrictModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(default="", max_length=20000)
    tags: list[str] = Field(default_factory=list)
    cover_url: str | None = Field(default=None, max_length=500)


class StoryUpdateRequest(StrictModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, max_length=20000)
    tags: list[str] | None = None
    cover_url: str | None = Field(default=None, max_length=500)
    status: str | None = None


class StoryCommentCreateRequest(StrictModel):
    body: str = Field(min_length=1, max_length=4000)


class PublicStoryOwnerView(BaseModel):
    display_name: str | None = None


class PublicStoryView(BaseModel):
    public_id: UUID
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    status: str
    cover_url: str | None = None
    reactions_count: int = 0
    comments_count: int = 0
    bookmarks_count: int = 0
    featured: bool = False
    published_at: datetime | None = None
    created_at: datetime
    author: PublicStoryOwnerView


class StoryOwnerView(BaseModel):
    public_id: UUID
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    status: str
    cover_url: str | None = None
    created_at: datetime
    updated_at: datetime


class StoryListResponse(BaseModel):
    items: list[PublicStoryView]
    meta: dict[str, Any] = Field(default_factory=dict)


class StoryCommentView(BaseModel):
    id: UUID
    body: str
    created_at: datetime
    author: PublicStoryOwnerView
