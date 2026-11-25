from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.schemas.market import (
    CartAddRequest,
    CartItemView,
    CartView,
    OrderItemView,
    OrderListResponse,
    OrderView,
    ProductCreateRequest,
    ProductListResponse,
    ProductOwnerView,
    PublicProductView,
    PublicShopView,
    ShopCreateRequest,
    ShopListResponse,
    ShopOwnerView,
)
from zooffer.services import market_service

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/shops", status_code=201)
async def create_shop(payload: ShopCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    shop = await market_service.create_shop(db, user, payload)
    return await _shop_owner_payload(db, shop)


@router.get("/shops")
async def list_shops(
    db: DbSession, city_id: int | None = Query(default=None), limit: int = Query(default=50, le=200)
) -> ShopListResponse:
    shops = await market_service.list_shops(db, city_id=city_id, limit=limit)
    items = [PublicShopView(**await market_service.shop_to_public(db, s)) for s in shops]
    return ShopListResponse(items=items, meta={"total": len(items)})


@router.get("/shops/{public_id}")
async def get_shop(public_id: uuid.UUID, db: DbSession) -> PublicShopView:
    shop = await market_service.get_shop(db, public_id)
    return PublicShopView(**await market_service.shop_to_public(db, shop))


@router.post("/shops/{public_id}/verify")
async def verify_shop(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    shop = await market_service.verify_shop(db, user, public_id)
    return await _shop_owner_payload(db, shop)


@router.post("/products", status_code=201)
async def create_product(payload: ProductCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    product = await market_service.create_product(db, user, payload)
    return await _product_owner_payload(db, product)


@router.get("/products")
async def list_products(
    db: DbSession,
    shop_public_id: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
) -> ProductListResponse:
    products = await market_service.list_products(db, shop_public_id=shop_public_id, limit=limit)
    items = [PublicProductView(**await market_service.product_to_public(db, p)) for p in products]
    return ProductListResponse(items=items, meta={"total": len(items)})


@router.get("/products/{public_id}")
async def get_product(public_id: uuid.UUID, db: DbSession) -> PublicProductView:
    product = await market_service.get_product(db, public_id)
    return PublicProductView(**await market_service.product_to_public(db, product))


@router.post("/products/{public_id}/publish")
async def publish_product(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    product = await market_service.publish_product(db, user, public_id)
    return await _product_owner_payload(db, product)


@router.post("/cart")
async def add_to_cart(payload: CartAddRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    await market_service.add_to_cart(db, user, payload.product_id, payload.quantity)
    return {"ok": True}


@router.get("/cart")
async def get_cart(auth: CurrentAuth, db: DbSession) -> CartView:
    user = auth.user
    items, total = await market_service.get_cart(db, user)
    views = []
    for ci, product in items:
        views.append(
            CartItemView(
                id=ci.id,
                product_id=product.public_id,
                quantity=ci.quantity,
                title=product.title,
                price_kopecks=product.price_kopecks,
            )
        )
    return CartView(items=views, total_kopecks=total)


@router.delete("/cart/{product_public_id}")
async def remove_from_cart(product_public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    await market_service.remove_from_cart(db, user, product_public_id)
    return {"ok": True}


@router.post("/orders", status_code=201)
async def create_order(auth: CurrentAuth, db: DbSession) -> OrderView:
    user = auth.user
    order = await market_service.create_order(db, user)
    items = await market_service.order_items(db, order.id)
    return OrderView(
        public_id=order.public_id,
        status=order.status,
        total_kopecks=order.total_kopecks,
        currency=order.currency,
        created_at=order.created_at,
        items=[
            OrderItemView(title=oi.title, price_kopecks=oi.price_kopecks, quantity=oi.quantity)
            for oi in items
        ],
    )


@router.get("/orders")
async def list_orders(auth: CurrentAuth, db: DbSession) -> OrderListResponse:
    user = auth.user
    orders = await market_service.list_orders(db, user)
    items = []
    for o in orders:
        ois = await market_service.order_items(db, o.id)
        items.append(
            OrderView(
                public_id=o.public_id,
                status=o.status,
                total_kopecks=o.total_kopecks,
                currency=o.currency,
                created_at=o.created_at,
                items=[
                    OrderItemView(
                        title=oi.title, price_kopecks=oi.price_kopecks, quantity=oi.quantity
                    )
                    for oi in ois
                ],
            )
        )
    return OrderListResponse(items=items, meta={"total": len(items)})


@router.get("/orders/{public_id}")
async def get_order(public_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> OrderView:
    user = auth.user
    order = await market_service.get_order(db, user, public_id)
    ois = await market_service.order_items(db, order.id)
    return OrderView(
        public_id=order.public_id,
        status=order.status,
        total_kopecks=order.total_kopecks,
        currency=order.currency,
        created_at=order.created_at,
        items=[
            OrderItemView(title=oi.title, price_kopecks=oi.price_kopecks, quantity=oi.quantity)
            for oi in ois
        ],
    )


async def _shop_owner_payload(db, shop) -> dict:
    data = await market_service.shop_to_owner(db, shop)
    return ShopOwnerView(**data).model_dump()


async def _product_owner_payload(db, product) -> dict:
    data = await market_service.product_to_owner(db, product)
    return ProductOwnerView(**data).model_dump()
