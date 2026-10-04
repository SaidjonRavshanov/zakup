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
from zakup.settings import IikoServerSettings, Settings

TEST_DB_URL = os.environ.get("ZAKUP_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:5432/zakup_test")
BACKEND_DIR = Path(__file__).resolve().parents[2]
ADMIN_TELEGRAM_ID = 1001
BOT_TOKEN = "123456:TEST-bot-token"
FAKE_IIKO_SERVERS = [
    IikoServerSettings(
        code=code,
        name=code.title(),
        base_url="http://fake-iiko/resto",  # type: ignore[arg-type]
        login="zakup",
        password="secret",  # type: ignore[arg-type]
        department_code=department,
    )
    for code, department in (("sebzar", "1"), ("drujba", "2"))
]


async def sign_in(client: AsyncClient, telegram_id: int, first_name: str = "Test") -> Response:
    return await client.post("/api/v1/auth/dev", json={"telegram_id": telegram_id, "first_name": first_name})


def bearer(session: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def onboard(
    client: AsyncClient, admin_headers: dict[str, str], telegram_id: int, grants: list[dict[str, str | None]]
) -> dict[str, str]:
    """Yangi xodim: kiradi → admin faollashtiradi, rol beradi → qayta kiradi. Natija — Authorization sarlavhasi."""
    await sign_in(client, telegram_id)
    listed = await client.get("/api/v1/identity/users", params={"status": "pending"}, headers=admin_headers)
    user_id = next(u["id"] for u in listed.json() if u["telegram_id"] == telegram_id)
    await client.post(f"/api/v1/identity/users/{user_id}/activate", headers=admin_headers)
    roles = await client.put(f"/api/v1/identity/users/{user_id}/roles", json={"grants": grants}, headers=admin_headers)
    assert roles.status_code == 204, roles.text
    session = await sign_in(client, telegram_id)
    assert session.status_code == 200, session.text
    return bearer(session.json())


@pytest.fixture(scope="session")
def settings() -> Settings:
    # _env_file=None: lokal backend/.env (haqiqiy iiko parollari) testlarga tushmasin
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        env="test",
        database_url=TEST_DB_URL,  # type: ignore[arg-type]
        dev_auth_bypass=True,
        bootstrap_admin_ids=[ADMIN_TELEGRAM_ID],
        telegram_bot_token=BOT_TOKEN,  # type: ignore[arg-type]
        iiko_servers=FAKE_IIKO_SERVERS,
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
                " catalog.branches, platform.outbox, identity.users, iiko.links, iiko.sync_runs,"
                " procurement.purchase_requests, procurement.purchase_orders CASCADE"
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
