"""Tahlil va nazorat: haqiqiy oqim (zayavka → PO → qabul) ustida hisobotlar."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.conftest import Worker, onboard
from tests.integration.test_receiving_flow import FLOUR_IIKO, LINK_SQL, _confirmed_order, _photo, _query
from zakup.shared_kernel.ids import uuid7

pytestmark = pytest.mark.integration


async def _receive_with_issues(client: AsyncClient, h: dict[str, str], order_id: str) -> str:
    """20 kg buyurtma (10 500): 18 kg keldi, 2 kg brak, narx 11 000 (+4.8%) — dopuskdan tashqari."""
    line = (await client.get(f"/api/v1/receiving/orders/{order_id}/expected", headers=h)).json()["lines"][0]
    receipt_id = str(uuid7())
    response = await client.post(
        "/api/v1/receiving/receipts",
        json={
            "id": receipt_id,
            "order_id": order_id,
            "invoice_photo_id": await _photo(client, h),
            "lines": [
                {
                    "order_line_id": line["order_line_id"],
                    "qty": "18",
                    "price": "11000",
                    "qty_defect": "2",
                    "defect_reason": "Ho'l qop",
                }
            ],
        },
        headers=h,
    )
    assert response.json() == {"status": "DISPUTED"}, response.text
    return receipt_id


async def test_reports_on_real_flow(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, _ = await _confirmed_order(client, admin_headers, worker, engine)
    await _receive_with_issues(client, admin_headers, order_id)
    await worker.drain()

    summary = (await client.get("/api/v1/analytics/summary", headers=admin_headers)).json()
    # qabul qilingan: 16 kg x 11 000 = 176 000; brak 2 x 11 000; ortiqcha to'lov 16 x 500
    assert (Decimal(summary["purchases"]), summary["receipts"], summary["open_disputes"]) == (Decimal(176000), 1, 1)
    assert (Decimal(summary["defect_loss"]), Decimal(summary["overpay"]), Decimal(summary["savings"])) == (
        Decimal(22000),
        Decimal(8000),
        Decimal(0),
    )
    assert Decimal(summary["debt"]) == 0  # nizo ochiq — majburiyat bloklangan, qarzda emas

    (rating,) = (await client.get("/api/v1/analytics/suppliers", headers=admin_headers)).json()["items"]
    assert (rating["orders"], rating["receipts"]) == (1, 1)
    assert (Decimal(rating["short_rate"]), Decimal(rating["price_rate"])) == (Decimal(1), Decimal(1))
    assert Decimal(rating["defect_rate"]) == (Decimal(2) / 18).quantize(Decimal(rating["defect_rate"]))
    # 100 − 40 (kam) − 30 x 0.11 (brak) − 20 (narx) − 0 (o'z vaqtida) = 37
    assert rating["score"] == "37"

    (price,) = (await client.get("/api/v1/analytics/prices", headers=admin_headers)).json()["items"]
    assert (Decimal(price["qty"]), Decimal(price["avg_price"])) == (Decimal(16), Decimal(11000))
    assert Decimal(price["overpay"]) == 16 * (Decimal(11000) - Decimal(price["best_price"]))
    history = (await client.get(f"/api/v1/analytics/prices/{price['product_id']}", headers=admin_headers)).json()
    assert {p["source"] for p in history} == {"offer", "receipt"}

    control = (await client.get("/api/v1/analytics/control", headers=admin_headers)).json()["items"]
    (discrepancy,) = [c for c in control if c["kind"] == "discrepancy"]
    assert set(discrepancy["detail"].split(", ")) == {"defect", "price_up", "qty_under"}


async def test_stock_value_and_dead_stock(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    _, store_id = await _confirmed_order(client, admin_headers, worker, engine)
    (flour_id,) = (await _query(engine, LINK_SQL, kind="product", iiko_id=FLOUR_IIKO))[0]
    async with engine.begin() as conn:  # 30 kun oldin sarf bo'lgan, so'nggi 28 kunda — yo'q: neliquid
        await conn.execute(
            text(
                "INSERT INTO planning.consumption_daily VALUES"
                " (:s, :p, (now() AT TIME ZONE 'Asia/Tashkent')::date - 30, 5)"
            ),
            {"s": store_id, "p": flour_id},
        )
        await conn.execute(
            text("INSERT INTO planning.stock_current VALUES (:s, :p, 40, now())"), {"s": store_id, "p": flour_id}
        )
    stock = (await client.get("/api/v1/analytics/stock", headers=admin_headers)).json()
    (item,) = stock["items"]
    assert (item["dead"], item["days_cover"], Decimal(item["qty"])) == (True, None, Decimal(40))
    assert Decimal(stock["dead_value"]) == Decimal(stock["total_value"]) == Decimal(item["value"]) > 0


async def test_access_and_store_scope(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, store_id = await _confirmed_order(client, admin_headers, worker, engine)
    await _receive_with_issues(client, admin_headers, order_id)
    other = (await client.post("/api/v1/catalog/stores", json={"name": "Boshqa"}, headers=admin_headers)).json()["id"]

    keeper = await onboard(client, admin_headers, 9201, [{"role": "storekeeper", "store_id": store_id}])
    assert (await client.get("/api/v1/analytics/summary", headers=keeper)).status_code == 403

    buyer = await onboard(client, admin_headers, 9202, [{"role": "buyer", "store_id": other}])
    own = (await client.get("/api/v1/analytics/summary", headers=buyer)).json()
    assert (Decimal(own["purchases"]), own["receipts"]) == (0, 0)  # boshqa ombor ma'lumoti ko'rinmaydi
    assert (await client.get(f"/api/v1/analytics/summary?store_id={store_id}", headers=buyer)).status_code == 403
    assert (await client.get("/api/v1/analytics/control", headers=buyer)).status_code == 403  # nazorat — auditor

    bad = await client.get("/api/v1/analytics/suppliers?from=2026-10-10&to=2026-10-01", headers=admin_headers)
    assert bad.json()["code"] == "invalid_report"
