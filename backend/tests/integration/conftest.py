"""Integratsion testlar: haqiqiy PostgreSQL (zakup_test), migratsiyalar Alembic orqali."""

import os
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fakes.iiko_server import FakeIikoState, create_fake_iiko
from zakup.bootstrap import build_invoice_exporter, iiko_scope_factory, outbox_handlers
from zakup.entrypoints.api import create_app
from zakup.modules.integration_iiko.application.runs import RunNextSync
from zakup.modules.integration_iiko.infrastructure.client import HttpIikoGateway, PgAdvisoryLock
from zakup.platform.db import create_session_factory
from zakup.platform.outbox_relay import OutboxRelay
from zakup.settings import IikoServerSettings, Settings
from zakup.shared_kernel.auth import SYSTEM_USER_ID

TEST_DB_URL = os.environ.get("ZAKUP_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:5432/zakup_test")
BACKEND_DIR = Path(__file__).resolve().parents[2]
MEDIA_DIR = Path(tempfile.gettempdir()) / "zakup-test-media"
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
        media_dir=str(MEDIA_DIR),
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
                " procurement.purchase_requests, procurement.purchase_orders, receiving.attachments,"
                " iiko.invoice_exports, planning.stock_current, planning.consumption_daily, platform.daily_jobs CASCADE"
            )
        )
        # Tizim foydalanuvchisi migratsiyada yaratiladi — TRUNCATE'dan keyin qaytariladi
        await conn.execute(
            text(
                "INSERT INTO identity.users (id, telegram_id, full_name, locale, is_active)"
                " VALUES (:id, 0, 'Tizim', 'uz', false)"
            ),
            {"id": SYSTEM_USER_ID},
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


# ---------------------------------------------------------------- oqim testlari: worker (soxta iiko)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DB_URL)
    yield engine
    await engine.dispose()


@dataclass
class Worker:
    sync: RunNextSync
    relay: OutboxRelay
    export: object
    state: FakeIikoState

    async def drain(self) -> None:
        while await self.sync() | bool(await self.relay()) | await self.export():  # type: ignore[operator]
            pass


@pytest.fixture
def worker(engine: AsyncEngine, settings: Settings) -> Worker:
    state = FakeIikoState()
    sessions = create_session_factory(engine)
    gateway = HttpIikoGateway(
        FAKE_IIKO_SERVERS,
        PgAdvisoryLock(engine, wait_s=5),
        timeout_s=10,
        transport=httpx.ASGITransport(app=create_fake_iiko(state=state)),
    )
    clock = lambda: datetime(2026, 10, 3, 6, tzinfo=UTC)  # noqa: E731 — fixture nakladnoylari sanasi
    return Worker(
        sync=RunNextSync(gateway, iiko_scope_factory(sessions), clock=clock),
        relay=OutboxRelay(sessions, outbox_handlers()),
        export=build_invoice_exporter(settings, gateway, sessions),
        state=state,
    )
