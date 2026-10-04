"""iiko'dan ma'lumotnoma → zayavka → PO → qabul (foto bilan) → outbox → iiko kirimi (soxta server)."""

from uuid import uuid4

import pytest
from defusedxml.ElementTree import fromstring
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.conftest import Worker, onboard
from zakup.shared_kernel.ids import uuid7

pytestmark = pytest.mark.integration

FLOUR_IIKO = "dddddddd-0000-4000-8000-000000000001"
STORE_IIKO = "bbbbbbbb-0000-4000-8000-000000000011"  # Sebzar — Главный Склад
CASH_CARD = "eeeeeeee-0000-4000-8000-000000000002"  # НАЛ Азиз ака
LINK_SQL = "SELECT local_id FROM iiko.links WHERE kind = :kind AND iiko_id = CAST(:iiko_id AS uuid)"
PHOTO = b"\xff\xd8\xff\xe0fake-jpeg"


async def _query(engine: AsyncEngine, sql: str, **params: object) -> list[tuple[object, ...]]:
    async with engine.connect() as conn:
        return [tuple(row) for row in (await conn.execute(text(sql), params)).all()]


async def _confirmed_order(
    client: AsyncClient, h: dict[str, str], worker: Worker, engine: AsyncEngine
) -> tuple[str, str]:
    """iiko'dan sinxron → Un 20 kg zayavka → tasdiq → PO (yuborilgan). (order_id, store_id)."""
    for kind, extra in (("references", {}), ("purchase_prices", {"days": 7})):
        assert (
            await client.post("/api/v1/iiko/sync", json={"server_code": "sebzar", "kind": kind, **extra}, headers=h)
        ).status_code == 202
        await worker.drain()
    (store_id,) = (await _query(engine, LINK_SQL, kind="store", iiko_id=STORE_IIKO))[0]
    (flour_id,) = (await _query(engine, LINK_SQL, kind="product", iiko_id=FLOUR_IIKO))[0]

    request = await client.post(
        "/api/v1/procurement/requests", json={"store_id": str(store_id), "needed_by": "2099-01-01"}, headers=h
    )
    request_id = request.json()["id"]
    await client.post(
        f"/api/v1/procurement/requests/{request_id}/lines", json={"product_id": str(flour_id), "qty": "20"}, headers=h
    )
    await client.post(f"/api/v1/procurement/requests/{request_id}/submit", headers=h)
    (order_id,) = (await client.post(f"/api/v1/procurement/requests/{request_id}/approve", json={}, headers=h)).json()[
        "order_ids"
    ]
    assert (
        await client.post(f"/api/v1/procurement/orders/{order_id}/send", json={"channel": "phone"}, headers=h)
    ).status_code == 200
    return order_id, str(store_id)


async def _photo(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post(
        "/api/v1/receiving/attachments", content=PHOTO, headers={**headers, "Content-Type": "image/jpeg"}
    )
    assert response.status_code == 201, response.text
    photo_id: str = response.json()["id"]
    return photo_id


async def test_receipt_to_iiko_invoice(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, store_id = await _confirmed_order(client, admin_headers, worker, engine)
    keeper = await onboard(client, admin_headers, 8801, [{"role": "storekeeper", "store_id": store_id}])

    expected = (await client.get(f"/api/v1/receiving/orders/{order_id}/expected", headers=keeper)).json()
    (line,) = expected["lines"]
    # iiko nakladnoyidan oxirgi narx: 10 500 / kg, 20 kg
    assert (line["product_name"], line["base_unit"], line["qty"], line["price"]) == (
        "Мука высший сорт товар",
        "kg",
        "20.0000",
        "10500.0000",
    )

    body = {
        "id": str(uuid7()),
        "order_id": order_id,
        "invoice_photo_id": await _photo(client, keeper),
        "supplier_invoice_no": "N-77",
        "payment_method": "cash",
        "lines": [{"order_line_id": line["order_line_id"], "qty": "20.4", "price": "10500"}],  # +2% — dopuskda
    }
    assert (
        await client.post("/api/v1/receiving/receipts", json={**body, "invoice_photo_id": str(uuid4())}, headers=keeper)
    ).json()["code"] == "invalid_receipt"
    submitted = await client.post("/api/v1/receiving/receipts", json=body, headers=keeper)
    assert submitted.json() == {"status": "ACCEPTED"}
    # Oflayn navbat qayta yuborsa — dublikat yo'q
    assert (await client.post("/api/v1/receiving/receipts", json=body, headers=keeper)).json() == {"status": "ACCEPTED"}
    second = await client.post("/api/v1/receiving/receipts", json={**body, "id": str(uuid7())}, headers=keeper)
    assert second.status_code == 409

    order = (await client.get(f"/api/v1/procurement/orders/{order_id}", headers=admin_headers)).json()
    assert order["status"] == "RECEIVED"

    await worker.drain()  # outbox → navbat → iiko
    (document,) = [fromstring(doc) for doc in worker.state.imported]
    assert document.findtext("documentNumber", "").startswith("R-")
    assert (document.findtext("supplier"), document.findtext("defaultStore"), document.findtext("status")) == (
        CASH_CARD,
        STORE_IIKO,
        "PROCESSED",
    )
    assert [(i.findtext("product"), i.findtext("amount"), i.findtext("price")) for i in document.iter("item")] == [
        (FLOUR_IIKO, "20.4000", "10500.0000")
    ]
    receipt = (await client.get("/api/v1/receiving/receipts", headers=keeper)).json()[0]
    assert (receipt["export_status"], receipt["status"]) == ("exported", "ACCEPTED")

    # Qayta urinish (masalan, javob yo'qolgan) — iiko'da shu raqam bor, yangi hujjat yaratilmaydi
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE iiko.invoice_exports SET status = 'failed', next_attempt_at = now() - interval '1 minute'")
        )
    await worker.drain()
    assert len(worker.state.imported) == 1
    assert (await _query(engine, "SELECT status FROM iiko.invoice_exports")) == [("done",)]


async def test_dispute_blocks_export_until_resolved(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, _ = await _confirmed_order(client, admin_headers, worker, engine)
    line = (await client.get(f"/api/v1/receiving/orders/{order_id}/expected", headers=admin_headers)).json()["lines"][0]
    receipt_id = str(uuid7())
    response = await client.post(
        "/api/v1/receiving/receipts",
        json={
            "id": receipt_id,
            "order_id": order_id,
            "invoice_photo_id": await _photo(client, admin_headers),
            "lines": [{"order_line_id": line["order_line_id"], "qty": "20", "price": "12000"}],  # +14% narx
        },
        headers=admin_headers,
    )
    assert response.json() == {"status": "DISPUTED"}
    await worker.drain()
    assert worker.state.imported == []  # nizo ochiq — kirim yo'q

    detail = (await client.get(f"/api/v1/receiving/receipts/{receipt_id}", headers=admin_headers)).json()
    assert [(d["kind"], d["within_tolerance"]) for d in detail["discrepancies"]] == [("price_up", False)]
    assert detail["dispute"]["resolution"] is None

    resolved = await client.post(
        f"/api/v1/receiving/receipts/{receipt_id}/resolve",
        json={"resolution": "accepted", "comment": "Yangi prays bo'yicha"},
        headers=admin_headers,
    )
    assert resolved.status_code == 204
    await worker.drain()
    (document,) = [fromstring(doc) for doc in worker.state.imported]
    assert document.findtext("status") == "NEW"  # nizoli qabul — buxgalter tekshiradi
    photo = await client.get(f"/api/v1/receiving/attachments/{detail['invoice_photo_id']}", headers=admin_headers)
    assert (photo.content, photo.headers["content-type"]) == (PHOTO, "image/jpeg")


async def test_only_receivers_of_the_store(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, _ = await _confirmed_order(client, admin_headers, worker, engine)
    other_store = await client.post("/api/v1/catalog/stores", json={"name": "Boshqa"}, headers=admin_headers)
    keeper = await onboard(client, admin_headers, 8802, [{"role": "storekeeper", "store_id": other_store.json()["id"]}])
    assert (await client.get(f"/api/v1/receiving/orders/{order_id}/expected", headers=keeper)).status_code == 403
    bad = await client.post(
        "/api/v1/receiving/attachments", content=b"x", headers={**keeper, "Content-Type": "text/plain"}
    )
    assert bad.json()["code"] == "invalid_receipt"
