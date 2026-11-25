from __future__ import annotations

import uuid

from sqlalchemy import select

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import CartItem, Order, OrderItem, Product, Profile, Shop


async def _get_shop(db, public_id):
    s = await db.scalar(select(Shop).where(Shop.public_id == public_id))
    if s is None:
        raise NotFoundError("Магазин не найден", code="shop_not_found")
    return s


async def _get_product(db, public_id):
    p = await db.scalar(select(Product).where(Product.public_id == public_id))
    if p is None:
        raise NotFoundError("Товар не найден", code="product_not_found")
    return p


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_shop(db, user, payload) -> Shop:
    shop = Shop(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        owner_id=user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        city_id=payload.city_id,
        status="pending",
    )
    db.add(shop)
    await db.commit()
    await db.refresh(shop)
    return shop


async def verify_shop(db, user, public_id) -> Shop:
    if getattr(user, "role", None) not in {"admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    shop = await _get_shop(db, public_id)
    shop.verified = True
    shop.status = "approved"
    await db.commit()
    await db.refresh(shop)
    return shop


async def list_shops(db, *, city_id=None, status="approved", limit=50):
    q = select(Shop).where(Shop.status == status)
    if city_id is not None:
        q = q.where(Shop.city_id == city_id)
    rows = (await db.scalars(q)).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def get_shop(db, public_id):
    return await _get_shop(db, public_id)


async def create_product(db, user, payload) -> Product:
    shop = await _get_shop(db, payload.shop_id)
    if shop.owner_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    if shop.status != "approved":
        raise ValidationAppError("Магазин не опубликован", code="shop_not_approved")
    product = Product(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        shop_id=shop.id,
        category_id=payload.category_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        price_kopecks=payload.price_kopecks,
        stock=payload.stock,
        status="draft",
        image_url=payload.image_url,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def publish_product(db, user, public_id) -> Product:
    product = await _get_product(db, public_id)
    shop = await db.get(Shop, product.shop_id)
    if shop is None or shop.owner_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    product.status = "published"
    await db.commit()
    await db.refresh(product)
    return product


async def list_products(db, *, shop_public_id=None, status="published", limit=50):
    q = select(Product).where(Product.status == status)
    if shop_public_id is not None:
        shop = await _get_shop(db, shop_public_id)
        q = q.where(Product.shop_id == shop.id)
    rows = (await db.scalars(q)).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def get_product(db, public_id):
    return await _get_product(db, public_id)


async def add_to_cart(db, user, product_public_id, quantity) -> CartItem:
    product = await _get_product(db, product_public_id)
    if product.status != "published":
        raise ValidationAppError("Товар недоступен", code="product_unavailable")
    existing = await db.scalar(
        select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product.id)
    )
    if existing is not None:
        existing.quantity += quantity
        await db.commit()
        await db.refresh(existing)
        return existing
    item = CartItem(id=uuid.uuid4(), user_id=user.id, product_id=product.id, quantity=quantity)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_cart(db, user):
    rows = (await db.scalars(select(CartItem).where(CartItem.user_id == user.id))).all()
    items = []
    total = 0
    for ci in rows:
        product = await db.get(Product, ci.product_id)
        if product is None:
            continue
        items.append((ci, product))
        total += product.price_kopecks * ci.quantity
    return items, total


async def remove_from_cart(db, user, product_public_id):
    product = await _get_product(db, product_public_id)
    item = await db.scalar(
        select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product.id)
    )
    if item is None:
        raise NotFoundError("Товар не в корзине", code="cart_item_not_found")
    await db.delete(item)
    await db.commit()


async def create_order(db, user) -> Order:
    items, total = await get_cart(db, user)
    if not items:
        raise ValidationAppError("Корзина пуста", code="empty_cart")
    order = Order(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        buyer_id=user.id,
        status="created",
        total_kopecks=total,
    )
    db.add(order)
    await db.flush()
    for ci, product in items:
        oi = OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=product.id,
            title=product.title,
            price_kopecks=product.price_kopecks,
            quantity=ci.quantity,
        )
        db.add(oi)
        product.stock = max(0, product.stock - ci.quantity)
    # clear cart
    await db.execute(select(CartItem).where(CartItem.user_id == user.id))
    from sqlalchemy import delete

    await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    await db.commit()
    await db.refresh(order)
    return order


async def list_orders(db, user):
    rows = (await db.scalars(select(Order).where(Order.buyer_id == user.id))).all()
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows)


async def get_order(db, user, public_id):
    o = await db.scalar(
        select(Order).where(Order.public_id == public_id, Order.buyer_id == user.id)
    )
    if o is None:
        raise NotFoundError("Заказ не найден", code="order_not_found")
    return o


async def order_items(db, order_id):
    rows = (await db.scalars(select(OrderItem).where(OrderItem.order_id == order_id))).all()
    return list(rows)


async def shop_to_public(db, shop) -> dict:
    return {
        "public_id": shop.public_id,
        "name": shop.name,
        "description": shop.description,
        "city_id": shop.city_id,
        "verified": shop.verified,
        "created_at": shop.created_at,
        "owner": {"display_name": await _owner_name(db, shop.owner_id)},
    }


async def shop_to_owner(db, shop) -> dict:
    return {
        "public_id": shop.public_id,
        "name": shop.name,
        "description": shop.description,
        "city_id": shop.city_id,
        "status": shop.status,
        "verified": shop.verified,
        "created_at": shop.created_at,
        "updated_at": shop.updated_at,
    }


async def product_to_public(db, product, shop=None) -> dict:
    if shop is None:
        shop = await db.get(Shop, product.shop_id)
    return {
        "public_id": product.public_id,
        "title": product.title,
        "description": product.description,
        "price_kopecks": product.price_kopecks,
        "stock": product.stock,
        "image_url": product.image_url,
        "created_at": product.created_at,
        "shop": await shop_to_public(db, shop) if shop is not None else None,
    }


async def product_to_owner(db, product) -> dict:
    return {
        "public_id": product.public_id,
        "title": product.title,
        "description": product.description,
        "price_kopecks": product.price_kopecks,
        "stock": product.stock,
        "status": product.status,
        "image_url": product.image_url,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
