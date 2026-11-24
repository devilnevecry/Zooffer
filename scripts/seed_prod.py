"""Seed production reference data: dictionaries, plans and system settings.

Unlike ``seed_dev.py`` this script never creates demo users, demo animals,
demo listings, demo partners or placeholder photos. It is idempotent and safe to
re-run after a deploy.

Usage (from the repository root):

    .venv\\Scripts\\python scripts\\seed_prod.py
    .venv\\Scripts\\python scripts\\seed_prod.py --stars-plus 1 --stars-premium 1

Prices in Stars are the real charge amount. ``--keep-placeholder`` leaves the
"price not approved" flag on, which makes production purchases fail closed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from seed_dev import BREEDS, REGIONS
from sqlalchemy import select
from zooffer.config import settings
from zooffer.db.models import Breed, City, Plan, Region, SystemSetting
from zooffer.db.session import SessionLocal, dispose_engine
from zooffer.services.admin_service import SETTING_DEFAULTS

# Reference plan catalogue. ``price_kopecks`` is informational for Stars-only
# launches; the charged amount is ``stars_amount``.
PLAN_SPECS: list[dict[str, object]] = [
    {
        "code": "free",
        "name": "Базовый",
        "description": "Дневной лимит свайпов, избранное и сообщения.",
        "price_kopecks": 0,
        "stars_amount": None,
        "period_days": 30,
        "entitlements": [],
        "sort_order": 0,
    },
    {
        "code": "plus",
        "name": "Zooffer Plus",
        "description": "Безлимитные свайпы, отмена последнего свайпа и расширенная галерея.",
        "price_kopecks": 29900,
        "stars_amount": 1,
        "period_days": 30,
        "entitlements": ["unlimited_swipes", "undo", "extended_photos", "ad_free"],
        "sort_order": 10,
    },
    {
        "code": "premium",
        "name": "Zooffer Premium",
        "description": "Всё из Plus, приоритетная модерация и продвижение объявлений.",
        "price_kopecks": 59900,
        "stars_amount": 1,
        "period_days": 30,
        "entitlements": [
            "unlimited_swipes",
            "undo",
            "see_who_liked",
            "boost",
            "extended_photos",
            "priority_moderation",
            "ad_free",
        ],
        "sort_order": 20,
    },
]


async def _seed_dictionaries(db) -> None:  # type: ignore[no-untyped-def]
    for code, name, cities in REGIONS:
        region = await db.scalar(select(Region).where(Region.code == code))
        if region is None:
            region = Region(code=code, name=name, slug=code.lower())
            db.add(region)
            await db.flush()
        for slug, city_name, latitude, longitude in cities:
            city = await db.scalar(select(City).where(City.slug == slug))
            if city is None:
                db.add(
                    City(
                        region_id=region.id,
                        name=city_name,
                        slug=slug,
                        latitude=latitude,
                        longitude=longitude,
                    )
                )
    for species, slug, name in BREEDS:
        breed = await db.scalar(
            select(Breed).where(Breed.species == species, Breed.slug == slug)
        )
        if breed is None:
            db.add(Breed(species=species, name=name, slug=slug))
    await db.commit()


async def _seed_plans(
    db,  # type: ignore[no-untyped-def]
    *,
    stars_plus: int,
    stars_premium: int,
    placeholder: bool,
) -> None:
    for spec in PLAN_SPECS:
        values = dict(spec)
        if values["code"] == "plus":
            values["stars_amount"] = stars_plus
        elif values["code"] == "premium":
            values["stars_amount"] = stars_premium
        values["is_placeholder_price"] = placeholder and values["code"] != "free"
        values["is_active"] = True
        plan = await db.scalar(select(Plan).where(Plan.code == values["code"]))
        if plan is None:
            db.add(Plan(**values))  # type: ignore[arg-type]
        else:
            for key, value in values.items():
                setattr(plan, key, value)
    await db.commit()


async def _seed_settings(db) -> None:  # type: ignore[no-untyped-def]
    defaults = {
        **SETTING_DEFAULTS,
        "free_daily_swipes": settings.free_daily_swipes,
        "enable_telegram": True,
    }
    for key, value in defaults.items():
        row = await db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value={"value": value}))
    await db.commit()


async def seed(*, stars_plus: int, stars_premium: int, placeholder: bool) -> None:
    async with SessionLocal() as db:
        await _seed_dictionaries(db)
        await _seed_plans(
            db,
            stars_plus=stars_plus,
            stars_premium=stars_premium,
            placeholder=placeholder,
        )
        await _seed_settings(db)
        first_region = await db.scalar(select(Region.id).limit(1))
        if first_region is None:
            raise RuntimeError("reference data seeding failed")
    print("Production reference data seeded: regions, cities, breeds, plans, settings.")
    print(
        f"Stars prices: plus={stars_plus}, premium={stars_premium}, placeholder={placeholder}"
    )
    print("No demo users, listings, partners or photos were created.")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Zooffer production reference data."
    )
    parser.add_argument("--stars-plus", type=int, default=1)
    parser.add_argument("--stars-premium", type=int, default=1)
    parser.add_argument(
        "--keep-placeholder",
        action="store_true",
        help="Keep is_placeholder_price=true so production purchases stay blocked.",
    )
    args = parser.parse_args()
    if args.stars_plus <= 0 or args.stars_premium <= 0:
        parser.error("Stars prices must be positive integers")
    try:
        await seed(
            stars_plus=args.stars_plus,
            stars_premium=args.stars_premium,
            placeholder=args.keep_placeholder,
        )
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
