from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ServiceProfileCreateRequest(StrictModel):
    category: str
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(default="", max_length=4000)
    city_id: int | None = None
    price_from_kopecks: int | None = Field(default=None, ge=0)
    formats: list[str] = Field(default_factory=list)
    experience_years: int | None = Field(default=None, ge=0, le=60)


class ServiceProfileUpdateRequest(StrictModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    description: str | None = Field(default=None, max_length=4000)
    city_id: int | None = None
    price_from_kopecks: int | None = Field(default=None, ge=0)
    formats: list[str] | None = None
    experience_years: int | None = Field(default=None, ge=0, le=60)


class ServiceReviewCreateRequest(StrictModel):
    rating: int = Field(ge=1, le=5)
    body: str = Field(default="", max_length=2000)
    booking_ref: str | None = Field(default=None, max_length=80)


class PublicServiceOwnerView(BaseModel):
    display_name: str | None = None


class PublicServiceProfileView(BaseModel):
    public_id: UUID
    category: str
    title: str
    description: str
    city_id: int | None = None
    price_from_kopecks: int | None = None
    formats: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    verified: bool = False
    rating_avg: float | None = None
    reviews_count: int = 0
    created_at: datetime
    owner: PublicServiceOwnerView


class ServiceProfileOwnerView(BaseModel):
    public_id: UUID
    category: str
    status: str
    title: str
    description: str
    city_id: int | None = None
    price_from_kopecks: int | None = None
    formats: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    verified: bool = False
    rating_avg: float | None = None
    reviews_count: int = 0
    created_at: datetime
    updated_at: datetime


class ServiceProfileListResponse(BaseModel):
    items: list[PublicServiceProfileView]
    meta: dict[str, Any] = Field(default_factory=dict)


class ServiceReviewView(BaseModel):
    id: UUID
    rating: int
    body: str
    created_at: datetime
    author: PublicServiceOwnerView


class ServiceReviewListResponse(BaseModel):
    items: list[ServiceReviewView]
    meta: dict[str, Any] = Field(default_factory=dict)
