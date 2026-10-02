"""Integratsion testlar: haqiqiy PostgreSQL (zakup_test), migratsiyalar Alembic orqali."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from zakup.entrypoints.api import create_app
from zakup.settings import Settings

TEST_DB_URL = os.environ.get("ZAKUP_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:5432/zakup_test")
BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(env="test", database_url=TEST_DB_URL, dev_auth_bypass=True)  # type: ignore[arg-type]


@pytest.fixture(scope="session", autouse=True)
def _migrate(settings: Settings) -> None:
    os.environ["ZAKUP_DATABASE_URL"] = TEST_DB_URL
    from zakup.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE catalog.suppliers, platform.outbox"))
    await engine.dispose()


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
    ):
        yield http
