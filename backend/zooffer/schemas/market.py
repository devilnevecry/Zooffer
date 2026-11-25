from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShopCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=4000)
    city_id: int | None = None


class ProductCreateRequest(StrictModel):
    shop_id: UUID
    category_id: UUID | None = None
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    price_kopecks: int = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=500)


class CartAddRequest(StrictModel):
    product_id: UUID
    quantity: int = Field(default=1, ge=1)


class OrderCreateRequest(StrictModel):
    pass


class PublicMarketOwnerView(BaseModel):
    display_name: str | None = None


class PublicShopView(BaseModel):
    public_id: UUID
    name: str
    description: str
    city_id: int | None = None
    verified: bool = False
    created_at: datetime
    owner: PublicMarketOwnerView


class ShopOwnerView(BaseModel):
    public_id: UUID
    name: str
    description: str
    city_id: int | None = None
    status: str
    verified: bool = False
    created_at: datetime
    updated_at: datetime


class PublicProductView(BaseModel):
    public_id: UUID
    title: str
    description: str
    price_kopecks: int
    stock: int
    image_url: str | None = None
    created_at: datetime
    shop: PublicShopView | None = None


class ProductOwnerView(BaseModel):
    public_id: UUID
    title: str
    description: str
    price_kopecks: int
    stock: int
    status: str
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ShopListResponse(BaseModel):
    items: list[PublicShopView]
    meta: dict[str, Any] = Field(default_factory=dict)


class ProductListResponse(BaseModel):
    items: list[PublicProductView]
    meta: dict[str, Any] = Field(default_factory=dict)


class CartItemView(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    title: str
    price_kopecks: int


class CartView(BaseModel):
    items: list[CartItemView]
    total_kopecks: int


class OrderItemView(BaseModel):
    title: str
    price_kopecks: int
    quantity: int


class OrderView(BaseModel):
    public_id: UUID
    status: str
    total_kopecks: int
    currency: str
    created_at: datetime
    items: list[OrderItemView] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    items: list[OrderView]
    meta: dict[str, Any] = Field(default_factory=dict)
