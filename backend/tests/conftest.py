from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Test configuration must be set before importing application modules.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://zooffer:zooffer_dev_password@localhost:5432/zooffer_test"
)
os.environ["SESSION_SECRET"] = "test-session-secret-0123456789abcdef0123456789abcdef"
os.environ["SECRET_PEPPER"] = "test-pepper-0123456789abcdef0123456789abcdef"
os.environ["COOKIE_SECURE"] = "false"
os.environ["PAYMENT_PROVIDER"] = "fake"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_UNIT_TESTS_ONLY"
os.environ["TELEGRAM_BOT_USERNAME"] = "zooffer_test_bot"
os.environ["HIBP_ENABLED"] = "false"

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from zooffer.config import settings
from zooffer.core.rate_limit import limiter
from zooffer.db.base import Base
from zooffer.db.session import get_db
from zooffer.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


@pytest_asyncio.fixture
async def engine():
    test_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(migrate_database: None, engine) -> None:
    table_names = [f'"{table.name}"' for table in Base.metadata.sorted_tables]
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
    limiter.clear_local()
    yield


@pytest_asyncio.fixture
async def db(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine) -> AsyncClient:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_client(client: AsyncClient) -> AsyncClient:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "Correct horse battery staple",
            "first_name": "Анна",
            "last_name": "Петрова",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert response.status_code == 201, response.text
    csrf = response.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return client
