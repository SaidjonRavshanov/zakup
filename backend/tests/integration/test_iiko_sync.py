"""iiko sinxronizatsiyasi: API navbatga qo'yadi → worker qadami soxta iiko serveridan o'qiydi → catalog."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fakes.iiko_server import FakeIikoState, create_fake_iiko
from tests.integration.conftest import FAKE_IIKO_SERVERS, TEST_DB_URL, bearer, sign_in
from zakup.bootstrap import iiko_scope_factory
from zakup.modules.integration_iiko.application.runs import RunNextSync
from zakup.modules.integration_iiko.infrastructure.client import HttpIikoGateway, PgAdvisoryLock
from zakup.platform.db import create_session_factory

pytestmark = pytest.mark.integration

SERVERS = FAKE_IIKO_SERVERS
NOW = datetime(2026, 10, 3, 6, 0, tzinfo=UTC)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DB_URL)
    yield engine
    await engine.dispose()


def _worker(engine: AsyncEngine, state: FakeIikoState) -> RunNextSync:
    gateway = HttpIikoGateway(
        SERVERS,
        PgAdvisoryLock(engine, wait_s=5),
        timeout_s=10,
        transport=httpx.ASGITransport(app=create_fake_iiko(state=state)),
    )
    return RunNextSync(gateway, iiko_scope_factory(create_session_factory(engine)), clock=lambda: NOW)


async def _query(engine: AsyncEngine, sql: str) -> list[tuple[object, ...]]:
    async with engine.connect() as conn:
        return [tuple(row) for row in (await conn.execute(text(sql))).all()]


async def _enqueue(client: AsyncClient, headers: dict[str, str], server: str, kind: str, **extra: object) -> str:
    response = await client.post(
        "/api/v1/iiko/sync", json={"server_code": server, "kind": kind, **extra}, headers=headers
    )
    assert response.status_code == 202, response.text
    run_id: str = response.json()["id"]
    return run_id


async def test_reference_sync_end_to_end(
    client: AsyncClient, admin_headers: dict[str, str], engine: AsyncEngine
) -> None:
    state = FakeIikoState()
    await _enqueue(client, admin_headers, "sebzar", "references")
    assert await _worker(engine, state)()
    assert not await _worker(engine, state)()  # navbat bo'sh

    overview = (await client.get("/api/v1/iiko/sync", headers=admin_headers)).json()
    (run,) = overview["runs"]
    assert run["status"] == "done", run["error"]
    assert run["stats"]["products_new"] == 2
    assert run["stats"]["products_skipped_unit"] == 1  # "порц" birlikli tovar
    assert [s["code"] for s in overview["servers"]] == ["sebzar", "drujba"]

    # iiko sessiyasi: bitta, yopilgan
    assert (state.opened, state.peak_sessions, state.active) == (1, 1, set())

    assert await _query(engine, "SELECT name, code FROM catalog.branches ORDER BY code") == [
        ("Tarnov Sebzar", "1"),
        ("Tarnov Drujba", "2"),
    ]
    stores = await _query(
        engine,
        "SELECT s.name, b.code FROM catalog.stores s JOIN catalog.branches b ON b.id = s.branch_id"
        " ORDER BY b.code, s.name",
    )
    assert stores == [("Бар склад", "1"), ("Главный Склад", "1"), ("Главный склад", "2")]
    products = await _query(engine, "SELECT name, article, base_unit FROM catalog.products ORDER BY article")
    assert products == [("Кола 0,5л", "147200", "pcs"), ("Мука высший сорт товар", "147317", "kg")]
    assert await _query(
        engine,
        "SELECT p.name, c.name FROM catalog.products p JOIN catalog.product_categories c ON c.id = p.category_id "
        "ORDER BY p.article",
    ) == [("Кола 0,5л", "Товары"), ("Мука высший сорт товар", "Бакалея")]

    # НАЛ + ПЕР → bitta yetkazuvchi; ombor-kontragent va o'chirilgan — yo'q; noto'g'ri STIR — None
    suppliers = await _query(
        engine, "SELECT name, inn, payment_methods, contacts->>'phone' FROM catalog.suppliers ORDER BY name"
    )
    assert suppliers == [
        ('"BIO NATURAL FOOD"MCHJ', None, [], None),
        ("Азиз ака (Алайский)", "305123456", ["cash", "transfer"], "+998971221002"),
    ]


async def test_second_server_reuses_shared_entities(
    client: AsyncClient, admin_headers: dict[str, str], engine: AsyncEngine
) -> None:
    state = FakeIikoState()
    for server in ("sebzar", "drujba"):
        await _enqueue(client, admin_headers, server, "references")
        assert await _worker(engine, state)()

    counts = await _query(
        engine,
        "SELECT (SELECT count(*) FROM catalog.stores), (SELECT count(*) FROM catalog.products),"
        " (SELECT count(*) FROM catalog.suppliers), (SELECT count(DISTINCT server_code) FROM iiko.links)",
    )
    assert counts == [(3, 2, 2, 2)]
    assert state.peak_sessions == 1


async def test_purchase_prices_from_invoices(
    client: AsyncClient, admin_headers: dict[str, str], engine: AsyncEngine
) -> None:
    state = FakeIikoState()
    await _enqueue(client, admin_headers, "sebzar", "references")
    await _worker(engine, state)()
    await _enqueue(client, admin_headers, "sebzar", "purchase_prices", days=7)
    assert await _worker(engine, state)()

    overview = (await client.get("/api/v1/iiko/sync", headers=admin_headers)).json()
    prices_run = next(r for r in overview["runs"] if r["kind"] == "purchase_prices")
    assert prices_run["status"] == "done", prices_run["error"]
    assert prices_run["stats"]["invoices_unknown_supplier"] == 1  # ombor-kontragentdan ko'chirish
    assert prices_run["stats"]["invoices_skipped"] == 1  # NEW (o'tkazilmagan)

    offers = await _query(
        engine,
        "SELECT s.name, p.name, o.pack_unit, o.pack_factor, o.price, o.price_valid_from::text"
        " FROM catalog.supplier_products o JOIN catalog.suppliers s ON s.id = o.supplier_id"
        " JOIN catalog.products p ON p.id = o.product_id ORDER BY p.article",
    )
    assert [(o[1], o[2], str(o[3]), str(o[4]), o[5]) for o in offers] == [
        ("Кола 0,5л", "pcs", "1.0000", "6000.0000", "2026-10-02"),
        ("Мука высший сорт товар", "kg", "1.0000", "10500.0000", "2026-10-02"),  # eng oxirgi nakladnoy narxi
    ]
    sources = await _query(engine, "SELECT DISTINCT source FROM catalog.supplier_price_history")
    assert sources == [("iiko",)]


async def test_only_admin_requests_sync_and_duplicates_conflict(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await sign_in(client, 4242)
    listed = await client.get("/api/v1/identity/users", params={"status": "pending"}, headers=admin_headers)
    user_id = next(u["id"] for u in listed.json() if u["telegram_id"] == 4242)
    await client.post(f"/api/v1/identity/users/{user_id}/activate", headers=admin_headers)
    await client.put(
        f"/api/v1/identity/users/{user_id}/roles", json={"grants": [{"role": "buyer"}]}, headers=admin_headers
    )
    buyer = bearer((await sign_in(client, 4242)).json())

    body = {"server_code": "sebzar", "kind": "references"}
    assert (await client.post("/api/v1/iiko/sync", json=body, headers=buyer)).status_code == 403
    assert (await client.get("/api/v1/iiko/sync", headers=buyer)).status_code == 200
    assert (await client.post("/api/v1/iiko/sync", json=body, headers=admin_headers)).status_code == 202
    assert (await client.post("/api/v1/iiko/sync", json=body, headers=admin_headers)).status_code == 409
    unknown = await client.post("/api/v1/iiko/sync", json={**body, "server_code": "istirohat"}, headers=admin_headers)
    assert unknown.status_code == 404


async def test_auth_failure_marks_run_failed(
    client: AsyncClient, admin_headers: dict[str, str], engine: AsyncEngine
) -> None:
    state = FakeIikoState(password="другой")
    await _enqueue(client, admin_headers, "sebzar", "references")
    assert await _worker(engine, state)()
    (run,) = (await client.get("/api/v1/iiko/sync", headers=admin_headers)).json()["runs"]
    assert run["status"] == "failed"
    assert "IikoAuthError" in run["error"]
    # Blok bo'shatilgan: keyingi ish kutib qolmaydi
    await _enqueue(client, admin_headers, "sebzar", "references")
    assert await _worker(engine, FakeIikoState())()
