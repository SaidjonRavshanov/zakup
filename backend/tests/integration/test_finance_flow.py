"""Qabul → majburiyat (outbox) → to'lov zayavkasi → tasdiq → to'lov (nakladnoyga taqsimlash); nizo bloki; qarzdor
yetkazuvchiga yangi buyurtma — faqat admin."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.conftest import Worker, onboard
from tests.integration.test_receiving_flow import (
    FLOUR_IIKO,
    LINK_SQL,
    PHOTO,
    STORE_IIKO,
    _confirmed_order,
    _photo,
    _query,
)
from zakup.shared_kernel.ids import uuid7

pytestmark = pytest.mark.integration


async def _receive(
    client: AsyncClient, h: dict[str, str], order_id: str, *, qty: str = "20", price: str = "10500"
) -> tuple[str, str]:
    """(receipt_id, status)."""
    line = (await client.get(f"/api/v1/receiving/orders/{order_id}/expected", headers=h)).json()["lines"][0]
    receipt_id = str(uuid7())
    response = await client.post(
        "/api/v1/receiving/receipts",
        json={
            "id": receipt_id,
            "order_id": order_id,
            "invoice_photo_id": await _photo(client, h),
            "lines": [{"order_line_id": line["order_line_id"], "qty": qty, "price": price}],
        },
        headers=h,
    )
    return receipt_id, response.json()["status"]


async def _account(client: AsyncClient, h: dict[str, str], supplier_id: str) -> dict[str, object]:
    response = await client.get(f"/api/v1/finance/suppliers/{supplier_id}", headers=h)
    assert response.status_code == 200, response.text
    account: dict[str, object] = response.json()
    return account


async def test_partial_payment_is_allocated_to_invoice(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, _ = await _confirmed_order(client, admin_headers, worker, engine)
    _, status = await _receive(client, admin_headers, order_id)
    assert status == "ACCEPTED"
    await worker.drain()  # outbox → majburiyat

    accountant = await onboard(client, admin_headers, 8901, [{"role": "accountant", "store_id": None}])
    (balance,) = (await client.get("/api/v1/finance/suppliers", headers=accountant)).json()
    assert (balance["debt"], balance["overdue"], balance["open_count"]) == ("210000.00", "0", 1)
    supplier_id = balance["supplier_id"]
    account = await _account(client, accountant, supplier_id)
    (obligation,) = account["obligations"]  # type: ignore[misc]
    assert (obligation["status"], obligation["outstanding"], obligation["receipt_number"][:2]) == (
        "OPEN",
        "210000.00",
        "R-",
    )

    def pay(amount: str) -> dict[str, object]:
        return {
            "supplier_id": supplier_id,
            "method": "transfer",
            "lines": [{"obligation_id": obligation["id"], "amount": amount}],
        }

    created = await client.post("/api/v1/finance/payments", json=pay("100000"), headers=accountant)
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]
    # 100 000 band — qolgan 110 000 dan ko'pini ikkinchi zayavkaga qo'yib bo'lmaydi
    over = await client.post("/api/v1/finance/payments", json=pay("150000"), headers=accountant)
    assert over.json()["code"] == "invalid_payment"

    assert (await client.post(f"/api/v1/finance/payments/{payment_id}/pay", json={}, headers=accountant)).json()[
        "code"
    ] == "invalid_transition"
    assert (await client.post(f"/api/v1/finance/payments/{payment_id}/approve", headers=accountant)).status_code == 403
    assert (
        await client.post(f"/api/v1/finance/payments/{payment_id}/approve", headers=admin_headers)
    ).status_code == 204

    proof = await client.post(
        "/api/v1/finance/attachments", content=PHOTO, headers={**accountant, "Content-Type": "image/jpeg"}
    )
    paid = await client.post(
        f"/api/v1/finance/payments/{payment_id}/pay", json={"proof_id": proof.json()["id"]}, headers=accountant
    )
    assert paid.status_code == 204, paid.text

    account = await _account(client, accountant, supplier_id)
    (obligation,) = account["obligations"]  # type: ignore[misc]
    assert (obligation["status"], obligation["paid"], obligation["outstanding"], obligation["reserved"]) == (
        "PARTIALLY_PAID",
        "100000.00",
        "110000.00",
        "0",
    )
    detail = (await client.get(f"/api/v1/finance/payments/{payment_id}", headers=accountant)).json()
    assert (detail["status"], detail["number"][:2], detail["total"]) == ("PAID", "P-", "100000.00")
    assert detail["lines"][0]["receipt_number"] == obligation["receipt_number"]
    file = await client.get(f"/api/v1/finance/attachments/{detail['proof_id']}", headers=accountant)
    assert file.content == PHOTO

    # Qoldiqni to'liq to'lash → PAID, ro'yxatdan chiqadi
    rest = (await client.post("/api/v1/finance/payments", json=pay("110000"), headers=accountant)).json()["id"]
    await client.post(f"/api/v1/finance/payments/{rest}/approve", headers=admin_headers)
    assert (await client.post(f"/api/v1/finance/payments/{rest}/pay", json={}, headers=accountant)).status_code == 204
    assert (await client.get("/api/v1/finance/suppliers", headers=accountant)).json() == []
    assert await _query(engine, "SELECT status, paid FROM finance.obligations") == [("PAID", Decimal("210000.00"))]


async def test_open_dispute_blocks_payment(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, _ = await _confirmed_order(client, admin_headers, worker, engine)
    receipt_id, status = await _receive(client, admin_headers, order_id, price="12000")  # +14% narx
    assert status == "DISPUTED"
    await worker.drain()

    (balance,) = (await client.get("/api/v1/finance/suppliers", headers=admin_headers)).json()
    assert (balance["debt"], balance["blocked"]) == ("0", "240000.00")
    account = await _account(client, admin_headers, balance["supplier_id"])
    (obligation,) = account["obligations"]  # type: ignore[misc]
    assert obligation["status"] == "BLOCKED"
    blocked = await client.post(
        "/api/v1/finance/payments",
        json={
            "supplier_id": balance["supplier_id"],
            "method": "cash",
            "lines": [{"obligation_id": obligation["id"], "amount": "1000"}],
        },
        headers=admin_headers,
    )
    assert blocked.json()["code"] == "invalid_payment"

    await client.post(
        f"/api/v1/receiving/receipts/{receipt_id}/resolve",
        json={"resolution": "accepted", "comment": "Yangi prays"},
        headers=admin_headers,
    )
    await worker.drain()
    account = await _account(client, admin_headers, balance["supplier_id"])
    assert [o["status"] for o in account["obligations"]] == ["OPEN"]  # type: ignore[attr-defined]


async def test_overdue_supplier_order_needs_admin(
    client: AsyncClient, admin_headers: dict[str, str], worker: Worker, engine: AsyncEngine
) -> None:
    order_id, store_id = await _confirmed_order(client, admin_headers, worker, engine)
    await _receive(client, admin_headers, order_id)
    await worker.drain()
    async with engine.begin() as conn:  # nakladnoy muddati o'tib ketgan
        await conn.execute(text("UPDATE finance.obligations SET due_date = due_date - 5"))
    (balance,) = (await client.get("/api/v1/finance/suppliers", headers=admin_headers)).json()
    assert balance["overdue"] == "210000.00"

    (flour_id,) = (await _query(engine, LINK_SQL, kind="product", iiko_id=FLOUR_IIKO))[0]
    assert (await _query(engine, LINK_SQL, kind="store", iiko_id=STORE_IIKO))[0][0] is not None
    request = await client.post(
        "/api/v1/procurement/requests", json={"store_id": store_id, "needed_by": "2099-01-02"}, headers=admin_headers
    )
    request_id = request.json()["id"]
    await client.post(
        f"/api/v1/procurement/requests/{request_id}/lines",
        json={"product_id": str(flour_id), "qty": "5"},
        headers=admin_headers,
    )
    await client.post(f"/api/v1/procurement/requests/{request_id}/submit", headers=admin_headers)

    buyer = await onboard(client, admin_headers, 8902, [{"role": "buyer", "store_id": None}])
    denied = await client.post(f"/api/v1/procurement/requests/{request_id}/approve", json={}, headers=buyer)
    assert (denied.status_code, denied.json()["code"]) == (403, "approval_limit")
    assert (
        "просроч"
        in (
            await client.post(
                f"/api/v1/procurement/requests/{request_id}/approve",
                json={},
                headers={**buyer, "Accept-Language": "ru"},
            )
        ).json()["message"]
    )
    approved = await client.post(f"/api/v1/procurement/requests/{request_id}/approve", json={}, headers=admin_headers)
    assert approved.status_code == 200, approved.text
