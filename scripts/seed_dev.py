"""Seed the local development database with demo content.

The script is idempotent: running it twice will not duplicate users, animals,
listings, photos, favorites, matches, conversations or partner offers.

Usage (from the repository root):

    .venv\\Scripts\\python scripts\\seed_dev.py

Demo accounts all use the password ``ZoofferDemo2026!``:

    anna@example.com
    mikhail@example.com
    elena@example.com
    dmitry@example.com
    olga@example.com

Photos are generated locally as clearly marked development placeholders. They are
never presented as real animal photography.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import delete, func, select
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Animal,
    AnimalPhoto,
    Breed,
    City,
    Conversation,
    ConversationParticipant,
    Favorite,
    Listing,
    Match,
    Message,
    Notification,
    Partner,
    PartnerOffer,
    Plan,
    Region,
    User,
)
from zooffer.db.session import SessionLocal, dispose_engine
from zooffer.schemas.listing import (
    AnimalCreateRequest,
    ListingCreateRequest,
)
from zooffer.services import auth_service, listing_service
from zooffer.services.media import process_and_store_image

DEMO_PASSWORD = "ZoofferDemo2026!"

REGIONS: list[tuple[str, str, list[tuple[str, str, float, float]]]] = [
    (
        "MSK",
        "Москва",
        [("moscow", "Москва", 55.7558, 37.6173)],
    ),
    (
        "MOS",
        "Московская область",
        [
            ("khimki", "Химки", 55.8892, 37.4450),
            ("podolsk", "Подольск", 55.4312, 37.5458),
            ("mytishchi", "Мытищи", 55.9116, 37.7308),
        ],
    ),
    (
        "SPB",
        "Санкт-Петербург",
        [("saint-petersburg", "Санкт-Петербург", 59.9343, 30.3351)],
    ),
    (
        "LEN",
        "Ленинградская область",
        [("vsevolozhsk", "Всеволожск", 60.0204, 30.6369)],
    ),
    (
        "TAT",
        "Татарстан",
        [("kazan", "Казань", 55.7963, 49.1088)],
    ),
    (
        "SVE",
        "Свердловская область",
        [("ekaterinburg", "Екатеринбург", 56.8389, 60.6057)],
    ),
    (
        "NVS",
        "Новосибирская область",
        [("novosibirsk", "Новосибирск", 55.0084, 82.9357)],
    ),
    (
        "KRD",
        "Краснодарский край",
        [
            ("krasnodar", "Краснодар", 45.0355, 38.9753),
            ("sochi", "Сочи", 43.6028, 39.7342),
        ],
    ),
]

BREEDS: list[tuple[str, str, str]] = [
    ("dog", "labrador-retriever", "Лабрадор-ретривер"),
    ("dog", "german-shepherd", "Немецкая овчарка"),
    ("dog", "welsh-corgi", "Вельш-корги"),
    ("dog", "siberian-husky", "Сибирский хаски"),
    ("dog", "pug", "Мопс"),
    ("dog", "jack-russell", "Джек-рассел-терьер"),
    ("dog", "beagle", "Бигль"),
    ("dog", "pomeranian", "Померанский шпиц"),
    ("dog", "golden-retriever", "Золотистый ретривер"),
    ("dog", "french-bulldog", "Французский бульдог"),
    ("cat", "british-shorthair", "Британская короткошёрстная"),
    ("cat", "maine-coon", "Мейн-кун"),
    ("cat", "scottish-fold", "Шотландская вислоухая"),
    ("cat", "sphynx", "Канадский сфинкс"),
    ("cat", "bengal", "Бенгальская"),
    ("cat", "domestic-shorthair", "Домашняя короткошёрстная"),
]

PLANS: list[dict[str, object]] = [
    {
        "code": "free",
        "name": "Базовый",
        "description": "20 свайпов в день, избранное и сообщения.",
        "price_kopecks": 0,
        "stars_amount": None,
        "period_days": 30,
        "entitlements": [],
        "sort_order": 0,
        "is_placeholder_price": False,
    },
    {
        "code": "plus",
        "name": "Zooffer Plus",
        "description": (
            "Безлимитные свайпы, отмена последнего свайпа и расширенная галерея."
        ),
        "price_kopecks": 29900,
        "stars_amount": 150,
        "period_days": 30,
        "entitlements": [
            "unlimited_swipes",
            "undo",
            "extended_photos",
            "ad_free",
        ],
        "sort_order": 10,
        "is_placeholder_price": True,
    },
    {
        "code": "premium",
        "name": "Zooffer Premium",
        "description": (
            "Всё из Plus, приоритетная модерация и продвижение объявлений."
        ),
        "price_kopecks": 59900,
        "stars_amount": 300,
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
        "is_placeholder_price": True,
    },
]

PARTNERS: list[dict[str, object]] = [
    {
        "name": "Зоомагазин «Лапа»",
        "slug": "lapa-demo",
        "description": "Демонстрационный партнёр Zooffer. Корма, амуниция и уход.",
        "offers": [
            {
                "title": "−15% на первый заказ корма",
                "description": "Скидка на сухие и влажные корма для собак и кошек.",
                "category": "food",
                "discount_code": "LAPA15",
                "destination_url": "https://example.com/zooffer/lapa-food",
                "terms": "Демонстрационное предложение. Не является публичной офертой.",
                "is_featured": True,
                "sort_order": 0,
            },
            {
                "title": "Бесплатная доставка от 3 000 ₽",
                "description": "Доставка по городу при заказе от указанной суммы.",
                "category": "stores",
                "discount_code": None,
                "destination_url": "https://example.com/zooffer/lapa-delivery",
                "terms": "Демонстрационное предложение. Условия уточняйте у партнёра.",
                "is_featured": False,
                "sort_order": 10,
            },
        ],
    },
    {
        "name": "Ветклиника «Добрый доктор»",
        "slug": "dobry-doktor-demo",
        "description": "Демонстрационный партнёр Zooffer. Профилактика и вакцинация.",
        "offers": [
            {
                "title": "Комплексный осмотр со скидкой 20%",
                "description": "Осмотр терапевта и консультация по уходу.",
                "category": "vet",
                "discount_code": "VET20",
                "destination_url": "https://example.com/zooffer/vet-checkup",
                "terms": "Демонстрационное предложение. Не является публичной офертой.",
                "is_featured": True,
                "sort_order": 20,
            },
        ],
    },
    {
        "name": "Груминг-студия «Пушистый день»",
        "slug": "pushistyi-den-demo",
        "description": "Демонстрационный партнёр Zooffer. Груминг и уход за шерстью.",
        "offers": [
            {
                "title": "Первый груминг — 2 500 ₽",
                "description": "Купание, сушка, стрижка и уход для небольших пород.",
                "category": "grooming",
                "discount_code": "GROOM2500",
                "destination_url": "https://example.com/zooffer/grooming",
                "terms": "Демонстрационное предложение. Стоимость зависит от породы.",
                "is_featured": False,
                "sort_order": 30,
            },
        ],
    },
]


@dataclass(slots=True)
class DemoListing:
    owner_email: str
    animal_name: str
    species: str
    breed_slug: str
    sex: str
    birth_date: date
    colour: str
    size: str
    purpose: str
    title: str
    description: str
    price_kopecks: int | None
    negotiable: bool
    city_slug: str
    vaccinated: bool
    has_pedigree: bool
    featured: bool = False
    palette: int = 0


DEMO_LISTINGS: list[DemoListing] = [
    DemoListing(
        owner_email="anna@example.com",
        animal_name="Арчи",
        species="dog",
        breed_slug="golden-retriever",
        sex="male",
        birth_date=date(2022, 5, 14),
        colour="Золотистый",
        size="large",
        purpose="sale",
        title="Золотистый ретривер Арчи — ласковый и активный",
        description=(
            "Арчи — спокойный и очень контактный пёс, вырос в семье с детьми. "
            "Знает базовые команды, спокойно остаётся дома и любит долгие прогулки. "
            "Привит по возрасту, есть ветеринарный паспорт. "
            "Передаётся с любимыми игрушками и кормом на первое время."
        ),
        price_kopecks=8500000,
        negotiable=True,
        city_slug="moscow",
        vaccinated=True,
        has_pedigree=True,
        featured=True,
        palette=0,
    ),
    DemoListing(
        owner_email="anna@example.com",
        animal_name="Мия",
        species="cat",
        breed_slug="british-shorthair",
        sex="female",
        birth_date=date(2021, 8, 2),
        colour="Голубой",
        size="medium",
        purpose="mating",
        title="Британская короткошёрстная Мия — вязка",
        description=(
            "Мия — тихая, ухоженная кошка с плотной плюшевой шерстью. "
            "Полностью привита, регулярно наблюдается у ветеринара. "
            "Ищем внимательного партнёра той же породы для плановой вязки. "
            "Готова познакомиться на нейтральной территории."
        ),
        price_kopecks=1500000,
        negotiable=True,
        city_slug="moscow",
        vaccinated=True,
        has_pedigree=True,
        featured=True,
        palette=1,
    ),
    DemoListing(
        owner_email="anna@example.com",
        animal_name="Тедди",
        species="dog",
        breed_slug="golden-retriever",
        sex="male",
        birth_date=date(2021, 4, 18),
        colour="Золотистый",
        size="large",
        purpose="mating",
        title="Тедди — золотистый ретривер для вязки",
        description=(
            "Тедди — спокойный и уверенный кобель с отличным экстерьером. "
            "Привит, прошёл проверку здоровья, есть родословная. "
            "Ищем невесту золотистого ретривера с документами. "
            "Поможем с организацией встречи и оставим контакты после знакомства."
        ),
        price_kopecks=1800000,
        negotiable=True,
        city_slug="moscow",
        vaccinated=True,
        has_pedigree=True,
        palette=3,
    ),
    DemoListing(
        owner_email="mikhail@example.com",
        animal_name="Рекс",
        species="dog",
        breed_slug="german-shepherd",
        sex="male",
        birth_date=date(2020, 3, 21),
        colour="Чепрачный",
        size="large",
        purpose="sale",
        title="Немецкая овчарка Рекс — надёжный компаньон",
        description=(
            "Рекс прошёл общий курс послушания и отлично работает на прогулке. "
            "Спокойно относится к другим собакам, знает команды рядом и ко мне. "
            "Привит, обработан от паразитов, есть родословная. "
            "Ищем ответственных хозяев с опытом содержания крупных пород."
        ),
        price_kopecks=4500000,
        negotiable=False,
        city_slug="saint-petersburg",
        vaccinated=True,
        has_pedigree=True,
        featured=True,
        palette=2,
    ),
    DemoListing(
        owner_email="mikhail@example.com",
        animal_name="Луна",
        species="dog",
        breed_slug="golden-retriever",
        sex="female",
        birth_date=date(2023, 1, 9),
        colour="Светло-золотистый",
        size="large",
        purpose="mating",
        title="Луна — золотистый ретривер для вязки",
        description=(
            "Луна — молодая и здоровая сука с отличным характером. "
            "Прошла полное обследование, привита, есть документы. "
            "Ищем кобеля золотистого ретривера с проверенным здоровьем. "
            "Поможем с организацией встречи и сопровождением."
        ),
        price_kopecks=2000000,
        negotiable=True,
        city_slug="saint-petersburg",
        vaccinated=True,
        has_pedigree=True,
        palette=3,
    ),
    DemoListing(
        owner_email="elena@example.com",
        animal_name="Барсик",
        species="cat",
        breed_slug="british-shorthair",
        sex="male",
        birth_date=date(2020, 11, 30),
        colour="Лавандовый",
        size="medium",
        purpose="mating",
        title="Барсик — британский кот для вязки",
        description=(
            "Барсик — крупный кот с густой шерстью и спокойным нравом. "
            "Привит, здоров, имеет метрику и отрицательные анализы. "
            "Ищем невесту британской короткошёрстной породы. "
            "Возможна вязка на территории кота или кошки."
        ),
        price_kopecks=1200000,
        negotiable=True,
        city_slug="kazan",
        vaccinated=True,
        has_pedigree=True,
        palette=4,
    ),
    DemoListing(
        owner_email="elena@example.com",
        animal_name="Соня",
        species="cat",
        breed_slug="maine-coon",
        sex="female",
        birth_date=date(2022, 2, 17),
        colour="Дымчатый",
        size="large",
        purpose="sale",
        title="Мейн-кун Соня — роскошная шерсть и добрый нрав",
        description=(
            "Соня — ласковая кошка с выразительным взглядом и пушистым хвостом. "
            "Приучена к лотку и когтеточке, спокойно переносит поездки. "
            "Привита, есть ветеринарные отметки. "
            "Ищем дом без других животных, где ей уделят достаточно внимания."
        ),
        price_kopecks=6000000,
        negotiable=True,
        city_slug="kazan",
        vaccinated=True,
        has_pedigree=False,
        palette=5,
    ),
    DemoListing(
        owner_email="dmitry@example.com",
        animal_name="Плюша",
        species="dog",
        breed_slug="welsh-corgi",
        sex="female",
        birth_date=date(2019, 6, 5),
        colour="Рыже-белый",
        size="small",
        purpose="adoption",
        title="Корги Плюша ищет новый дом",
        description=(
            "Плюша — добрая и воспитанная собака, которая оказалась в семье "
            "временно. Она спокойно гуляет, любит людей и быстро привыкает. "
            "Ищем ответственных хозяев без маленьких детей. "
            "Передаём бесплатно, с условием знакомства и поддержки после переезда."
        ),
        price_kopecks=None,
        negotiable=False,
        city_slug="ekaterinburg",
        vaccinated=True,
        has_pedigree=False,
        featured=True,
        palette=6,
    ),
    DemoListing(
        owner_email="dmitry@example.com",
        animal_name="Бим",
        species="dog",
        breed_slug="beagle",
        sex="male",
        birth_date=date(2021, 9, 12),
        colour="Трёхцветный",
        size="medium",
        purpose="sale",
        title="Бигль Бим — весёлый исследователь",
        description=(
            "Бим — энергичный и дружелюбный бигль, обожает прогулки и игры. "
            "Знает команды, хорошо ходит на поводке, не агрессивен к людям. "
            "Привит и обработан. "
            "Нужен активный хозяин, готовый много гулять и заниматься с собакой."
        ),
        price_kopecks=3500000,
        negotiable=True,
        city_slug="ekaterinburg",
        vaccinated=True,
        has_pedigree=False,
        palette=7,
    ),
    DemoListing(
        owner_email="olga@example.com",
        animal_name="Ева",
        species="cat",
        breed_slug="sphynx",
        sex="female",
        birth_date=date(2022, 7, 25),
        colour="Розовый",
        size="small",
        purpose="rehoming",
        title="Сфинкс Ева — нежная и общительная",
        description=(
            "Ева — очень ласковая кошка, которая любит быть рядом с человеком. "
            "Приучена к лотку, спокойно относится к детям. "
            "Привита, регулярно купается и ухаживает за кожей. "
            "Переезжает по семейным обстоятельствам, ищем заботливые руки."
        ),
        price_kopecks=1500000,
        negotiable=True,
        city_slug="novosibirsk",
        vaccinated=True,
        has_pedigree=False,
        palette=8,
    ),
    DemoListing(
        owner_email="olga@example.com",
        animal_name="Тайсон",
        species="dog",
        breed_slug="siberian-husky",
        sex="male",
        birth_date=date(2021, 12, 1),
        colour="Серо-белый",
        size="large",
        purpose="sale",
        title="Хаски Тайсон — энергичный пёс для активных людей",
        description=(
            "Тайсон — выносливый и любознательный хаски. "
            "Отлично ходит в упряжке, любит бег и долгие маршруты. "
            "Привит, есть ветеринарный паспорт. "
            "Ищем хозяев, готовых обеспечить нагрузку и безопасные прогулки."
        ),
        price_kopecks=5500000,
        negotiable=True,
        city_slug="novosibirsk",
        vaccinated=True,
        has_pedigree=True,
        palette=9,
    ),
]


PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((236, 196, 151), (191, 125, 77)),
    ((187, 201, 216), (111, 129, 150)),
    ((199, 210, 188), (112, 133, 109)),
    ((229, 207, 195), (171, 133, 116)),
    ((196, 190, 214), (124, 116, 150)),
    ((181, 208, 205), (95, 134, 134)),
    ((240, 209, 179), (196, 147, 105)),
    ((211, 201, 181), (134, 124, 99)),
    ((234, 196, 203), (177, 119, 132)),
    ((182, 203, 219), (100, 133, 159)),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ):
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _gradient(size: tuple[int, int], start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    _width, height = size
    column = Image.new("RGB", (1, height))
    pixels = column.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        pixels[0, y] = tuple(  # type: ignore[index]
            round(start[i] + (end[i] - start[i]) * ratio) for i in range(3)
        )
    return column.resize(size)


def _paw(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, fill: tuple[int, int, int, int]) -> None:
    draw.ellipse(
        (cx - int(95 * scale), cy - int(55 * scale), cx + int(95 * scale), cy + int(110 * scale)),
        fill=fill,
    )
    toes = [
        (-130, -85, -70, -20),
        (-55, -135, 0, -65),
        (30, -135, 85, -65),
        (105, -85, 165, -20),
    ]
    for x1, y1, x2, y2 in toes:
        draw.ellipse(
            (
                cx + int(x1 * scale),
                cy + int(y1 * scale),
                cx + int(x2 * scale),
                cy + int(y2 * scale),
            ),
            fill=fill,
        )


def _placeholder_image(palette_index: int, variant: int) -> bytes:
    start, end = PALETTES[palette_index % len(PALETTES)]
    if variant:
        start = tuple(min(255, channel + 14) for channel in start)  # type: ignore[assignment]
        end = tuple(max(0, channel - 10) for channel in end)  # type: ignore[assignment]
    size = (1200, 1500)
    image = _gradient(size, start, end).convert("RGBA")

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((120, -180, 1080, 780), fill=(255, 255, 255, 60))
    glow_draw.ellipse((-160, 900, 620, 1680), fill=(255, 255, 255, 34))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    image = Image.alpha_composite(image, glow)

    shapes = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shapes)
    _paw(draw, 600 + (variant * 40 - 20), 610, 2.1, (255, 255, 255, 48))
    draw.ellipse((740, 1030, 1120, 1410), outline=(255, 255, 255, 55), width=8)
    draw.ellipse((90, 230, 250, 390), outline=(255, 255, 255, 40), width=6)
    image = Image.alpha_composite(image, shapes)

    footer = Image.new("RGBA", size, (0, 0, 0, 0))
    footer_draw = ImageDraw.Draw(footer)
    footer_draw.rectangle((0, 1350, size[0], size[1]), fill=(24, 36, 54, 92))
    footer_draw.text((64, 1402), "ZOOFFER · DEMO IMAGE", font=_font(38), fill=(255, 255, 255, 214))
    footer_draw.text(
        (64, 1452),
        "Placeholder generated for local development",
        font=_font(26),
        fill=(255, 255, 255, 150),
    )
    image = Image.alpha_composite(image, footer)

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


async def _get_or_create_region(db, code: str, name: str) -> Region:  # type: ignore[no-untyped-def]
    region = await db.scalar(select(Region).where(Region.code == code))
    if region is None:
        region = Region(code=code, name=name, slug=code.lower())
        db.add(region)
        await db.flush()
    return region


async def _seed_dictionaries(db) -> None:  # type: ignore[no-untyped-def]
    for code, name, cities in REGIONS:
        region = await _get_or_create_region(db, code, name)
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
        breed = await db.scalar(select(Breed).where(Breed.species == species, Breed.slug == slug))
        if breed is None:
            db.add(Breed(species=species, name=name, slug=slug))
    await db.commit()


async def _seed_plans(db) -> None:  # type: ignore[no-untyped-def]
    for spec in PLANS:
        plan = await db.scalar(select(Plan).where(Plan.code == spec["code"]))
        if plan is None:
            db.add(Plan(**spec))  # type: ignore[arg-type]
        else:
            for key, value in spec.items():
                setattr(plan, key, value)
    await db.commit()


async def _seed_partners(db) -> None:  # type: ignore[no-untyped-def]
    now = utcnow()
    for partner_spec in PARTNERS:
        partner = await db.scalar(select(Partner).where(Partner.slug == partner_spec["slug"]))
        if partner is None:
            partner = Partner(
                name=partner_spec["name"],
                slug=partner_spec["slug"],
                description=partner_spec["description"],
                status="active",
            )
            db.add(partner)
            await db.flush()
        else:
            partner.name = partner_spec["name"]
            partner.description = partner_spec["description"]
            partner.status = "active"
        for offer_spec in partner_spec["offers"]:  # type: ignore[union-attr]
            offer = await db.scalar(
                select(PartnerOffer).where(
                    PartnerOffer.partner_id == partner.id,
                    PartnerOffer.title == offer_spec["title"],
                )
            )
            if offer is None:
                db.add(
                    PartnerOffer(
                        partner_id=partner.id,
                        starts_at=now - timedelta(days=7),
                        ends_at=now + timedelta(days=180),
                        status="active",
                        ad_label="Реклама",
                        erid="demo-erid-not-for-production",
                        **offer_spec,
                    )
                )
            else:
                offer.status = "active"
                offer.starts_at = now - timedelta(days=7)
                offer.ends_at = now + timedelta(days=180)
    await db.commit()


async def _get_or_create_user(db, spec: dict[str, str], city_id: int) -> User:  # type: ignore[no-untyped-def]
    existing = await auth_service.find_user_by_email(db, spec["email"])
    if existing is not None:
        return existing
    user = await auth_service.create_user_with_password(
        db,
        email=spec["email"],
        password=DEMO_PASSWORD,
        first_name=spec["first_name"],
        last_name=spec.get("last_name") or None,
        city_id=city_id,
        accepted_terms=True,
        accepted_privacy=True,
        marketing_opt_in=False,
        channel="seed",
    )
    user.onboarding_completed_at = utcnow()
    user.email_verified_at = utcnow()
    db.add(user)
    await db.commit()
    return user


async def _ensure_photos(db, animal: Animal, palette: int) -> int:  # type: ignore[no-untyped-def]
    existing = (
        await db.scalars(
            select(AnimalPhoto).where(AnimalPhoto.animal_id == animal.id).order_by(AnimalPhoto.position)
        )
    ).all()
    created = 0
    for position in range(len(existing), 2):
        processed = await process_and_store_image(_placeholder_image(palette, position))
        db.add(
            AnimalPhoto(
                animal_id=animal.id,
                storage_key=processed.full_key,
                position=position,
                width=processed.width,
                height=processed.height,
                content_hash=processed.content_hash,
                is_primary=position == 0,
                alt_text=f"{animal.name} — демонстрационное изображение",
            )
        )
        created += 1
    if created:
        await db.commit()
    return len(existing) + created


async def _seed_listing(db, spec: DemoListing) -> tuple[Animal, Listing]:  # type: ignore[no-untyped-def]
    user = await auth_service.find_user_by_email(db, spec.owner_email)
    if user is None:
        raise RuntimeError(f"demo user not found: {spec.owner_email}")
    breed = await db.scalar(
        select(Breed).where(Breed.species == spec.species, Breed.slug == spec.breed_slug)
    )
    city = await db.scalar(select(City).where(City.slug == spec.city_slug))
    if city is None:
        raise RuntimeError(f"city not found: {spec.city_slug}")

    animal = await db.scalar(
        select(Animal).where(Animal.owner_id == user.id, Animal.name == spec.animal_name)
    )
    if animal is None:
        animal = await listing_service.create_animal(
            db,
            user,
            AnimalCreateRequest(
                name=spec.animal_name,
                species=spec.species,  # type: ignore[arg-type]
                breed_id=breed.id if breed else None,
                breed_text=breed.name if breed else None,
                sex=spec.sex,  # type: ignore[arg-type]
                birth_date=spec.birth_date,
                colour=spec.colour,
                size=spec.size,  # type: ignore[arg-type]
                has_pedigree=spec.has_pedigree,
                pedigree_registry="FCI" if spec.has_pedigree else None,
                pedigree_number=f"DEMO-{spec.animal_name.upper()}" if spec.has_pedigree else None,
                vaccinated=spec.vaccinated,
                health_notes="Плановые осмотры пройдены. Демонстрационные данные.",
                description=spec.description,
            ),
        )

    await _ensure_photos(db, animal, spec.palette)

    listing = await db.scalar(select(Listing).where(Listing.animal_id == animal.id))
    if listing is None:
        listing = await listing_service.create_listing(
            db,
            user,
            ListingCreateRequest(
                animal_id=animal.public_id,
                purpose=spec.purpose,  # type: ignore[arg-type]
                title=spec.title,
                description=spec.description,
                price_kopecks=spec.price_kopecks,
                negotiable=spec.negotiable,
                city_id=city.id,
                region_id=city.region_id,
            ),
        )
        listing = await listing_service.publish_listing(db, user, listing.public_id)
    if spec.featured and not listing.is_featured:
        listing.is_featured = True
        await db.commit()
    return animal, listing


async def _ensure_favorite(db, user: User, listing: Listing) -> None:  # type: ignore[no-untyped-def]
    existing = await db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing.id)
    )
    if existing is None:
        db.add(Favorite(user_id=user.id, listing_id=listing.id))
        await db.commit()


async def _conversation_participants(db, conversation_id) -> set:  # type: ignore[no-untyped-def]
    rows = await db.scalars(
        select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id == conversation_id
        )
    )
    return set(rows.all())


async def _ensure_conversation(  # type: ignore[no-untyped-def]
    db,
    *,
    conversation_type: str,
    listing: Listing,
    animal: Animal,
    participants: list[User],
    message_specs: list[tuple[User, str, int]],
) -> Conversation:
    participant_ids = {user.id for user in participants}
    conversations = (
        await db.scalars(
            select(Conversation).where(
                Conversation.conversation_type == conversation_type,
                Conversation.listing_id == listing.id,
            )
        )
    ).all()
    conversation = None
    for candidate in conversations:
        if await _conversation_participants(db, candidate.id) == participant_ids:
            conversation = candidate
            break
    if conversation is not None:
        return conversation

    conversation = Conversation(
        id=uuid4(),
        public_id=uuid4(),
        conversation_type=conversation_type,
        listing_id=listing.id,
        animal_id=animal.id,
    )
    db.add(conversation)
    await db.flush()
    for user in participants:
        db.add(
            ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user.id,
                last_read_at=utcnow(),
            )
        )
    base_time = utcnow() - timedelta(hours=6)
    latest = base_time
    for index, (sender, body, minutes) in enumerate(message_specs):
        created_at = base_time + timedelta(minutes=minutes + index)
        latest = max(latest, created_at)
        db.add(
            Message(
                id=uuid4(),
                conversation_id=conversation.id,
                sender_id=sender.id,
                body=body,
                created_at=created_at,
            )
        )
    conversation.last_message_at = latest
    await db.commit()
    return conversation


async def _ensure_match(  # type: ignore[no-untyped-def]
    db, *, animal_a: Animal, animal_b: Animal, listing: Listing, messages: list[tuple[User, str, int]]
) -> None:
    first_id, second_id = sorted((animal_a.id, animal_b.id), key=str)
    existing = await db.scalar(
        select(Match).where(Match.animal_a_id == first_id, Match.animal_b_id == second_id)
    )
    first_animal = animal_a if animal_a.id == first_id else animal_b
    second_animal = animal_b if first_animal is animal_a else animal_a
    owner_a = await db.get(User, first_animal.owner_id)
    owner_b = await db.get(User, second_animal.owner_id)
    if owner_a is None or owner_b is None:
        raise RuntimeError("match owners missing")

    if existing is None:
        conversation = await _ensure_conversation(
            db,
            conversation_type="match",
            listing=listing,
            animal=animal_b,
            participants=[owner_a, owner_b],
            message_specs=messages,
        )
        db.add(
            Match(
                id=uuid4(),
                animal_a_id=first_id,
                animal_b_id=second_id,
                owner_a_id=first_animal.owner_id,
                owner_b_id=second_animal.owner_id,
                conversation_id=conversation.id,
            )
        )
        await db.commit()


async def _seed_interactions(  # type: ignore[no-untyped-def]
    db,
) -> None:
    anna = await auth_service.find_user_by_email(db, "anna@example.com")
    mikhail = await auth_service.find_user_by_email(db, "mikhail@example.com")
    elena = await auth_service.find_user_by_email(db, "elena@example.com")
    if anna is None or mikhail is None or elena is None:
        raise RuntimeError("demo users missing")

    async def find_listing(owner: User, animal_name: str) -> tuple[Animal, Listing]:
        animal = await db.scalar(
            select(Animal).where(Animal.owner_id == owner.id, Animal.name == animal_name)
        )
        if animal is None:
            raise RuntimeError(f"animal missing: {animal_name}")
        listing = await db.scalar(select(Listing).where(Listing.animal_id == animal.id))
        if listing is None:
            raise RuntimeError(f"listing missing: {animal_name}")
        return animal, listing

    anna_mia, anna_mia_listing = await find_listing(anna, "Мия")
    elena_barsik, elena_barsik_listing = await find_listing(elena, "Барсик")
    anna_archie, anna_archie_listing = await find_listing(anna, "Арчи")
    _, mikhail_rex_listing = await find_listing(mikhail, "Рекс")
    anna_teddy, _ = await find_listing(anna, "Тедди")
    mikhail_luna, mikhail_luna_listing = await find_listing(mikhail, "Луна")

    # Favorites for "Избранное" screens.
    await _ensure_favorite(db, anna, mikhail_rex_listing)
    await _ensure_favorite(db, anna, elena_barsik_listing)
    await _ensure_favorite(db, mikhail, anna_archie_listing)
    await _ensure_favorite(db, elena, anna_mia_listing)

    # A mutual mating like -> match + conversation with history.
    await _ensure_match(
        db,
        animal_a=anna_teddy,
        animal_b=mikhail_luna,
        listing=mikhail_luna_listing,
        messages=[
            (anna, "Здравствуйте! Луна и Тедди выглядят отличной парой. Расскажите о здоровье, пожалуйста.", 0),
            (mikhail, "Здравствуйте! Луна полностью привита, есть документы. Будем рады знакомству.", 14),
            (anna, "Отлично! Давайте созвонимся и обсудим удобное время встречи.", 22),
            (mikhail, "Договорились. Напишите, пожалуйста, когда вам удобно.", 31),
        ],
    )

    # A second match between the two British shorthairs.
    await _ensure_match(
        db,
        animal_a=anna_mia,
        animal_b=elena_barsik,
        listing=elena_barsik_listing,
        messages=[
            (elena, "Здравствуйте! Барсик спокойный и привитый. Готовы познакомиться с Мией.", 0),
            (anna, "Здравствуйте! Спасибо за отклик. Мия тоже здорова и привита.", 18),
            (elena, "Когда вам удобно встретиться на нейтральной территории?", 35),
        ],
    )

    # An inquiry conversation about a sale listing.
    await _ensure_conversation(
        db,
        conversation_type="inquiry",
        listing=anna_archie_listing,
        animal=anna_archie,
        participants=[mikhail, anna],
        message_specs=[
            (mikhail, "Здравствуйте! Арчи ещё ищет дом? Расскажите, как он относится к детям.", 0),
            (anna, "Здравствуйте! Да, ищет. С детьми ладит отлично, вырос в семье.", 20),
            (mikhail, "Спасибо! Можно ли приехать познакомиться на выходных?", 47),
            (anna, "Конечно. Напишите, пожалуйста, в какое время вам удобно.", 66),
        ],
    )

    # Notifications for the primary demo account.
    notifications = [
        ("matches", "Новая пара", "У вас взаимная симпатия с Луной.", {"kind": "match"}),
        ("messages", "Новое сообщение", "Михаил написал вам по объявлению «Арчи».", {"kind": "message"}),
        (
            "listing_moderation",
            "Объявление опубликовано",
            "«Золотистый ретривер Арчи» прошло автоматическую проверку.",
            {"kind": "listing"},
        ),
        (
            "partners",
            "Скидка от партнёра",
            "Зоомагазин «Лапа» дарит −15% на первый заказ.",
            {"kind": "partner"},
        ),
    ]
    for category, title, body, data in notifications:
        existing = await db.scalar(
            select(Notification).where(
                Notification.user_id == anna.id,
                Notification.title == title,
                Notification.body == body,
            )
        )
        if existing is None:
            db.add(
                Notification(
                    id=uuid4(),
                    user_id=anna.id,
                    category=category,
                    title=title,
                    body=body,
                    data=data,
                )
            )
    await db.commit()


async def _seed_users(db) -> None:  # type: ignore[no-untyped-def]
    city_by_slug = {city.slug: city for city in (await db.scalars(select(City))).all()}
    for spec in DEMO_USER_SPECS:
        city = city_by_slug[spec["city"]]
        await _get_or_create_user(db, spec, city.id)  # type: ignore[arg-type]


async def seed(*, reset: bool = False) -> None:
    async with SessionLocal() as db:
        if reset:
            emails = [spec["email"] for spec in DEMO_USER_SPECS]
            demo_users = [
                user
                for user in [await auth_service.find_user_by_email(db, email) for email in emails]
                if user is not None
            ]
            demo_ids = [user.id for user in demo_users]
            if demo_ids:
                conversation_ids = select(ConversationParticipant.conversation_id).where(
                    ConversationParticipant.user_id.in_(demo_ids)
                )
                await db.execute(
                    delete(Conversation).where(Conversation.id.in_(conversation_ids))
                )
            for user in demo_users:
                await db.delete(user)
            await db.commit()
            print("Removed existing demo users and their cascaded data.")

        await _seed_dictionaries(db)
        await _seed_plans(db)
        await _seed_partners(db)
        await _seed_users(db)

        for spec in DEMO_LISTINGS:
            animal, listing = await _seed_listing(db, spec)
            print(f"  listing: {listing.slug} ({animal.name})")

        await _seed_interactions(db)

        counts = {
            "users": await db.scalar(select(func.count()).select_from(User)),
            "regions": await db.scalar(select(func.count()).select_from(Region)),
            "cities": await db.scalar(select(func.count()).select_from(City)),
            "breeds": await db.scalar(select(func.count()).select_from(Breed)),
            "listings": await db.scalar(select(func.count()).select_from(Listing)),
            "matches": await db.scalar(select(func.count()).select_from(Match)),
        }
        print("\nSeed complete:")
        for key, value in counts.items():
            print(f"  {key}: {value}")
        print(f"\nDemo password for all accounts: {DEMO_PASSWORD}")


DEMO_USER_SPECS = [
    {
        "email": "anna@example.com",
        "first_name": "Анна",
        "last_name": "Смирнова",
        "city": "moscow",
    },
    {
        "email": "mikhail@example.com",
        "first_name": "Михаил",
        "last_name": "",
        "city": "saint-petersburg",
    },
    {
        "email": "elena@example.com",
        "first_name": "Елена",
        "last_name": "Кузнецова",
        "city": "kazan",
    },
    {
        "email": "dmitry@example.com",
        "first_name": "Дмитрий",
        "last_name": "",
        "city": "ekaterinburg",
    },
    {
        "email": "olga@example.com",
        "first_name": "Ольга",
        "last_name": "Петрова",
        "city": "novosibirsk",
    },
]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Zooffer development database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete demo users (cascades to their animals, listings and messages) first.",
    )
    args = parser.parse_args()
    try:
        await seed(reset=args.reset)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
