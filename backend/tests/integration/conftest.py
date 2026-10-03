"""Integratsion testlar: haqiqiy PostgreSQL (zakup_test), migratsiyalar Alembic orqali."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from zakup.entrypoints.api import create_app
from zakup.settings import Settings

TEST_DB_URL = os.environ.get("ZAKUP_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:5432/zakup_test")
BACKEND_DIR = Path(__file__).resolve().parents[2]
ADMIN_TELEGRAM_ID = 1001
BOT_TOKEN = "123456:TEST-bot-token"


async def sign_in(client: AsyncClient, telegram_id: int, first_name: str = "Test") -> Response:
    return await client.post("/api/v1/auth/dev", json={"telegram_id": telegram_id, "first_name": first_name})


def bearer(session: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        env="test",
        database_url=TEST_DB_URL,  # type: ignore[arg-type]
        dev_auth_bypass=True,
        bootstrap_admin_ids=[ADMIN_TELEGRAM_ID],
        telegram_bot_token=BOT_TOKEN,  # type: ignore[arg-type]
    )


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
        await conn.execute(
            text(
                "TRUNCATE catalog.suppliers, catalog.stores, catalog.products, catalog.product_categories,"
                " platform.outbox, identity.users CASCADE"
            )
        )
    await engine.dispose()


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
    ):
        yield http


@pytest.fixture
async def admin_headers(client: AsyncClient) -> dict[str, str]:
    response = await sign_in(client, ADMIN_TELEGRAM_ID, "Admin")
    assert response.status_code == 200, response.text
    return bearer(response.json())
