"""iiko qoldiq + sarf (OLAP) → planning; avto-zayavka qoralamasi "nega shuncha" bilan; ertalabki rejalashtiruvchi."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.conftest import Worker, onboard
from tests.integration.test_receiving_flow import FLOUR_IIKO, LINK_SQL, STORE_IIKO, _confirmed_order, _query
from zakup.bootstrap import build_daily_scheduler
from zakup.modules.integration_iiko.infrastructure.client import HttpIikoGateway
from zakup.platform.db import create_session_factory
from zakup.settings import Settings

pytestmark = pytest.mark.integration

BAR_STORE_IIKO = "bbbbbbbb-0000-4000-8000-000000000012"


async def _sync(client: AsyncClient, h: dict[str, str], worker: Worker, kind: str, **extra: Any) -> None:
    response = await client.post("/api/v1/iiko/sync", json={"server_code": "sebzar", "kind": kind, **extra}, headers=h)
    assert response.status_code == 202, response.text
    await worker.drain()


async def test_stock_and_consumption_are_imported(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    await _sync(client, admin_headers, worker, "references")
    await _sync(client, admin_headers, worker, "stock")
    await _sync(client, admin_headers, worker, "consumption", days=3)  # worker soati: 2026-10-03 → [09-30, 10-03)

    (store_id,) = (await _query(engine, LINK_SQL, kind="store", iiko_id=STORE_IIKO))[0]
    (flour_id,) = (await _query(engine, LINK_SQL, kind="product", iiko_id=FLOUR_IIKO))[0]
    consumption = await _query(
        engine,
        "SELECT day::text, qty FROM planning.consumption_daily WHERE store_id = :s AND product_id = :p ORDER BY day",
        s=store_id,
        p=flour_id,
    )
    # sotuv + ko'chirish hisoblanadi; inventarizatsiya, nol chiqim va oraliqdan tashqari kun — yo'q
    assert consumption == [("2026-09-30", Decimal(6)), ("2026-10-01", Decimal(8)), ("2026-10-02", Decimal(6))]
    stock = await _query(engine, "SELECT store_id, product_id, qty FROM planning.stock_current ORDER BY qty")
    assert (store_id, flour_id, Decimal("12.5")) in stock
    assert all(qty != 0 for *_, qty in stock)  # nol qoldiq saqlanmaydi; taom (DISH) bog'lanmagan — tashlandi

    runs = (await client.get("/api/v1/iiko/sync", headers=admin_headers)).json()["runs"]
    by_kind = {run["kind"]: run for run in runs}
    assert by_kind["consumption"]["stats"]["movements_skipped"] >= 1  # noma'lum ombor
    assert by_kind["stock"]["status"] == "done"


async def test_auto_request_explains_quantity(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, store_id = await _confirmed_order(client, admin_headers, worker, engine)  # 20 kg un yo'lda
    (flour_id,) = (await _query(engine, LINK_SQL, kind="product", iiko_id=FLOUR_IIKO))[0]
    order = (await client.get(f"/api/v1/procurement/orders/{order_id}", headers=admin_headers)).json()
    card = await client.put(
        "/api/v1/catalog/purchase-cards",
        json={
            "product_id": str(flour_id),
            "store_id": store_id,
            "mode": "auto",
            "safety_stock": "5",
            "coverage_days": 3,
            "primary_supplier_id": order["supplier_id"],
        },
        headers=admin_headers,
    )
    assert card.status_code in {200, 204}, card.text
    async with engine.begin() as conn:  # oxirgi 10 kun: 10 kg/kun; qoldiq 4 kg
        await conn.execute(
            text(
                "INSERT INTO planning.consumption_daily (store_id, product_id, day, qty)"
                " SELECT :s, :p, (now() AT TIME ZONE 'Asia/Tashkent')::date - d, 10 FROM generate_series(1, 10) AS d"
            ),
            {"s": store_id, "p": flour_id},
        )
        await conn.execute(
            text("INSERT INTO planning.stock_current VALUES (:s, :p, 4, now())"), {"s": store_id, "p": flour_id}
        )

    initiator = await onboard(client, admin_headers, 9101, [{"role": "initiator", "store_id": store_id}])
    assert (await client.post("/api/v1/procurement/auto-requests", json={}, headers=initiator)).status_code == 403

    run = (await client.post("/api/v1/procurement/auto-requests", json={}, headers=admin_headers)).json()
    assert (len(run["request_ids"]), run["lines"]) == (1, 1)
    detail = (await client.get(f"/api/v1/procurement/requests/{run['request_ids'][0]}", headers=admin_headers)).json()
    assert (detail["type"], detail["status"]) == ("auto", "DRAFT")
    (line,) = detail["lines"]
    # maqsad 10 x (1 + 3) + 5 = 45; mavjud 4 + 20 (yo'lda) = 24 → 21 kg (qadoq 1 kg)
    assert (Decimal(line["qty"]), Decimal(line["qty_suggested"])) == (Decimal(21), Decimal(21))
    calc = line["calc"]
    assert (Decimal(calc["avg_daily"]), Decimal(calc["in_transit"]), Decimal(calc["stock"])) == (
        Decimal(10),
        Decimal(20),
        Decimal(4),
    )
    assert (calc["days_observed"], calc["trigger"]) == ("10", "order_day")

    again = (await client.post("/api/v1/procurement/auto-requests", json={}, headers=admin_headers)).json()
    assert (again["request_ids"], again["skipped"]) == ([], {"already_today": 1})
    forced = (
        await client.post("/api/v1/procurement/auto-requests", json={"force": True}, headers=admin_headers)
    ).json()
    assert forced["skipped"] == {"in_open_request": 1}  # qoralamada turibdi — takrorlanmaydi

    # Zakupshik miqdorni o'zgartiradi — taklif saqlanadi (tasdiqlovchi farqni ko'radi)
    request_id = run["request_ids"][0]
    changed = await client.patch(
        f"/api/v1/procurement/requests/{request_id}/lines/{line['id']}", json={"qty": "25"}, headers=admin_headers
    )
    assert changed.status_code in {200, 204}, changed.text
    assert (
        await client.post(f"/api/v1/procurement/requests/{request_id}/submit", headers=admin_headers)
    ).status_code == 204
    line = (await client.get(f"/api/v1/procurement/requests/{request_id}", headers=admin_headers)).json()["lines"][0]
    assert (Decimal(line["qty"]), Decimal(line["qty_suggested"])) == (Decimal(25), Decimal(21))


async def test_morning_scheduler_runs_once_per_day(engine: AsyncEngine, settings: Settings) -> None:
    sessions = create_session_factory(engine)
    gateway = HttpIikoGateway(settings.iiko_servers, None, timeout_s=1)  # type: ignore[arg-type] — iiko chaqirilmaydi
    scheduler = build_daily_scheduler(settings, gateway, sessions)
    scheduler._clock = lambda: datetime(2026, 10, 4, 1, 30, tzinfo=UTC)  # Toshkent 06:30
    assert await scheduler()
    assert not await scheduler()  # shu kun — qayta emas
    runs = await _query(engine, "SELECT server_code, kind, params->>'days' FROM iiko.sync_runs ORDER BY 1, 2")
    # sarf tarixi yo'q — birinchi marta 28 kun
    assert runs == [
        ("drujba", "consumption", "28"),
        ("drujba", "purchase_prices", "2"),
        ("drujba", "stock", None),
        ("sebzar", "consumption", "28"),
        ("sebzar", "purchase_prices", "2"),
        ("sebzar", "stock", None),
    ]
    assert await _query(engine, "SELECT job FROM platform.daily_jobs ORDER BY job") == [
        ("auto_requests",),
        ("iiko_daily_sync",),
    ]
