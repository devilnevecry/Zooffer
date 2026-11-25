from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Shop(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "shops"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (Index("ix_shops_status_city", "status", "city_id"),)


class ProductCategory(Base, UUIDPrimaryKey):
    __tablename__ = "product_categories"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_categories.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Product(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "products"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    shop_id: Mapped[UUID] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_categories.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (Index("ix_products_shop_status", "shop_id", "status"),)


class CartItem(Base, UUIDPrimaryKey):
    __tablename__ = "cart_items"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_cart_items_user_product"),)


class Order(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "orders"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    buyer_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="created", index=True, nullable=False)
    total_kopecks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)

    __table_args__ = (Index("ix_orders_buyer_status", "buyer_id", "status"),)


class OrderItem(Base, UUIDPrimaryKey):
    __tablename__ = "order_items"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
