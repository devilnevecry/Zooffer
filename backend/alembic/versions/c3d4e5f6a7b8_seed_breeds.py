"""seed breeds

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-25 10:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BREEDS = [
    ("dog", "Лабрадор ретривер", "labrador-retriever"),
    ("dog", "Немецкая овчарка", "german-shepherd"),
    ("dog", "Золотистый ретривер", "golden-retriever"),
    ("dog", "Французский бульдог", "french-bulldog"),
    ("dog", "Бульдог", "bulldog"),
    ("dog", "Пудель", "poodle"),
    ("dog", "Бигль", "beagle"),
    ("dog", "Ротвейлер", "rottweiler"),
    ("dog", "Такса", "dachshund"),
    ("dog", "Йоркширский терьер", "yorkshire-terrier"),
    ("dog", "Боксер", "boxer"),
    ("dog", "Сибирский хаски", "siberian-husky"),
    ("dog", "Чихуахуа", "chihuahua"),
    ("dog", "Шпиц", "spitz"),
    ("dog", "Шнауцер", "schnauzer"),
    ("dog", "Кокер-спаниель", "cocker-spaniel"),
    ("dog", "Доберман", "doberman"),
    ("dog", "Мопс", "pug"),
    ("dog", "Шарпей", "shar-pei"),
    ("dog", "Акита", "akita"),
    ("cat", "Британская короткошёрстная", "british-shorthair"),
    ("cat", "Шотландская вислоухая", "scottish-fold"),
    ("cat", "Мейн-кун", "maine-coon"),
    ("cat", "Сиамская", "siamese"),
    ("cat", "Персидская", "persian"),
    ("cat", "Бенгальская", "bengal"),
    ("cat", "Сфинкс", "sphynx"),
    ("cat", "Рэгдолл", "ragdoll"),
    ("cat", "Абиссинская", "abyssinian"),
    ("cat", "Бурманская", "burmese"),
    ("cat", "Норвежская лесная", "norwegian-forest"),
    ("cat", "Русская голубая", "russian-blue"),
    ("cat", "Ориентальная", "oriental"),
    ("cat", "Экзотическая короткошёрстная", "exotic-shorthair"),
    ("cat", "Турецкая ангора", "turkish-angora"),
]


def upgrade() -> None:
    # Idempotent seed: skip breeds that already exist (from previous installs/seeds).
    for species, name, slug in BREEDS:
        op.execute(
            sa.text(
                "INSERT INTO breeds (species, name, slug) VALUES (:species, :name, :slug) "
                "ON CONFLICT (species, slug) DO NOTHING"
            ).bindparams(species=species, name=name, slug=slug)
        )


def downgrade() -> None:
    # Keep data on downgrade to avoid deleting user-referenced breeds.
    pass
