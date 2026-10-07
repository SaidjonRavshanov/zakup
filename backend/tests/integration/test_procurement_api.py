"""Zayavka → tasdiqlash → PO → yuborish → yetkazuvchi javobi (havola orqali) — to'liq oqim."""

from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.integration.conftest import onboard

pytestmark = pytest.mark.integration

API = "/api/v1/procurement"
CATALOG = "/api/v1/catalog"
NEEDED_BY = (date.today() + timedelta(days=2)).isoformat()


@dataclass
class World:
    store: str
    flour: str
    sugar: str
    don: str  # 25 kg qop, 250 000 → 10 000 / kg (arzonroq)
    shirin: str  # kg bo'yicha 10 500
    chef: dict[str, str]
    buyer: dict[str, str]
    approver: dict[str, str]


async def _create(client: AsyncClient, path: str, body: dict[str, object], headers: dict[str, str]) -> str:
    response = await client.post(path, json=body, headers=headers)
    assert response.status_code == 201, response.text
    created: str = response.json()["id"]
    return created


@pytest.fixture
async def world(client: AsyncClient, admin_headers: dict[str, str]) -> World:
    h = admin_headers
    store = await _create(client, f"{CATALOG}/stores", {"name": "Oshxona"}, h)
    flour = await _create(client, f"{CATALOG}/products", {"name": "Un", "base_unit": "kg"}, h)
    sugar = await _create(client, f"{CATALOG}/products", {"name": "Shakar", "base_unit": "kg"}, h)
    don = await _create(client, f"{CATALOG}/suppliers", {"name": "Don Mahsulot", "payment_terms": "prepay"}, h)
    shirin = await _create(client, f"{CATALOG}/suppliers", {"name": "Shirin", "payment_terms": "prepay"}, h)
    offer = {"pack_unit": "bag", "pack_factor": "25", "price": "250000"}
    await _create(client, f"{CATALOG}/suppliers/{don}/offers", {**offer, "product_id": flour}, h)
    await _create(client, f"{CATALOG}/suppliers/{don}/offers", {**offer, "product_id": sugar, "price": "400000"}, h)
    kg_offer = {"pack_unit": "kg", "pack_factor": "1", "price": "10500"}
    await _create(client, f"{CATALOG}/suppliers/{shirin}/offers", {**kg_offer, "product_id": flour}, h)
    return World(
        store=store,
        flour=flour,
        sugar=sugar,
        don=don,
        shirin=shirin,
        chef=await onboard(client, h, 7001, [{"role": "initiator", "store_id": store}]),
        buyer=await onboard(client, h, 7002, [{"role": "buyer", "store_id": store}]),
        approver=await onboard(client, h, 7003, [{"role": "approver"}]),
    )


async def _draft(client: AsyncClient, w: World, lines: list[tuple[str, str]]) -> str:
    request_id = await _create(client, f"{API}/requests", {"store_id": w.store, "needed_by": NEEDED_BY}, w.chef)
    for product, qty in lines:
        await _create(client, f"{API}/requests/{request_id}/lines", {"product_id": product, "qty": qty}, w.chef)
    return request_id


async def _submitted(client: AsyncClient, w: World, lines: list[tuple[str, str]]) -> str:
    request_id = await _draft(client, w, lines)
    assert (await client.post(f"{API}/requests/{request_id}/submit", headers=w.chef)).status_code == 204
    return request_id


async def test_full_flow_request_to_supplier_response(client: AsyncClient, world: World) -> None:
    w = world
    request_id = await _submitted(client, w, [(w.flour, "30"), (w.sugar, "10")])

    detail = (await client.get(f"{API}/requests/{request_id}", headers=w.chef)).json()
    assert detail["status"] == "PENDING_APPROVAL"
    # Avtomatik eng arzon yetkazuvchi: un — Don (10 000/kg), shakar — Don (16 000/kg).
    # Summa buyurtmadagidek qadoqqa yaxlitlangan: 30 kg un → 2 qop, 10 kg shakar → 1 qop
    assert [(ln["product_name"], ln["supplier_name"], ln["amount"]) for ln in detail["lines"]] == [
        ("Un", "Don Mahsulot", "500000.00"),
        ("Shakar", "Don Mahsulot", "400000.00"),
    ]
    assert detail["total"] == "900000.00"
    # Buyurtmaga qanday ketadi: qadoqqa yaxlitlangan — PO summasi bilan bir xil (pastda 900 000)
    assert [(ln["pack_unit"], ln["qty_packs"], ln["order_amount"]) for ln in detail["lines"]] == [
        ("bag", "2.0000", "500000.00"),
        ("bag", "1.0000", "400000.00"),
    ]
    assert detail["order_total"] == "900000.00"

    # Oshpaz tasdiqlay olmaydi; zakupshik limiti (2 mln) yetadi
    assert (await client.post(f"{API}/requests/{request_id}/approve", json={}, headers=w.chef)).status_code == 403
    approved = await client.post(f"{API}/requests/{request_id}/approve", json={}, headers=w.buyer)
    assert approved.status_code == 200, approved.text
    (order_id,) = approved.json()["order_ids"]  # bitta yetkazuvchi → bitta PO

    order = (await client.get(f"{API}/orders/{order_id}", headers=w.buyer)).json()
    assert order["status"] == "CREATED"
    # 30 kg → 2 qop (karralilik), 10 kg → 1 qop
    assert [(ln["product_name"], ln["qty_packs"], ln["amount"]) for ln in order["lines"]] == [
        ("Un", "2.0000", "500000.00"),
        ("Shakar", "1.0000", "400000.00"),
    ]
    assert order["total"] == "900000.00"
    request_after = (await client.get(f"{API}/requests/{request_id}", headers=w.chef)).json()
    assert request_after["status"] == "SPLIT"
    assert [o["number"] for o in request_after["orders"]] == [order["number"]]

    sent = await client.post(f"{API}/orders/{order_id}/send", json={"channel": "telegram"}, headers=w.buyer)
    assert sent.status_code == 200, sent.text
    assert "Un — 2 меш (50 кг)" in sent.json()["message"]
    token = sent.json()["response_url"].rsplit("/", 1)[1]

    public = await client.get(f"/api/v1/public/orders/{token}")
    assert public.status_code == 200
    assert "supplier_phone" not in public.json()
    line_ids = [ln["id"] for ln in public.json()["lines"]]

    # Narx +4% (dopusk 3%) → qayta tasdiqlash
    response = await client.post(
        f"/api/v1/public/orders/{token}/response",
        json={"lines": [{"line_id": line_ids[0], "kind": "price_changed", "price_per_pack": "260000"}]},
    )
    assert response.json()["status"] == "REAPPROVAL"
    approved_changes = await client.post(f"{API}/orders/{order_id}/approve-changes", headers=w.approver)
    assert approved_changes.json()["status"] == "CONFIRMED"
    final = (await client.get(f"{API}/orders/{order_id}", headers=w.buyer)).json()
    assert final["confirmed_total"] == "920000.00"

    assert (await client.get("/api/v1/public/orders/not-a-token")).status_code == 401


async def test_over_limit_needs_approver_and_flags(client: AsyncClient, world: World) -> None:
    w = world
    request_id = await _submitted(client, w, [(w.flour, "250")])  # 2.5 mln > zakupshik limiti
    denied = await client.post(f"{API}/requests/{request_id}/approve", json={}, headers=w.buyer)
    assert (denied.status_code, denied.json()["code"]) == (403, "approval_limit")
    assert (await client.post(f"{API}/requests/{request_id}/approve", json={}, headers=w.approver)).status_code == 200
    approvals = (await client.get(f"{API}/requests/{request_id}", headers=w.approver)).json()["approvals"]
    assert [(a["decision"], a["role_conflict"]) for a in approvals] == [("approved", False)]


async def test_partial_approval_splits_by_supplier(client: AsyncClient, world: World) -> None:
    w = world
    request_id = await _draft(client, w, [(w.flour, "5"), (w.sugar, "5")])
    detail = (await client.get(f"{API}/requests/{request_id}", headers=w.chef)).json()
    flour_line = next(ln for ln in detail["lines"] if ln["product_name"] == "Un")

    # Zakupshik unni Shirin'ga o'tkazadi (kg bo'yicha)
    shirin_offer = next(
        o["id"] for o in (await client.get(f"{CATALOG}/suppliers/{w.shirin}", headers=w.buyer)).json()["offers"]
    )
    chosen = await client.put(
        f"{API}/requests/{request_id}/lines/{flour_line['id']}/offer", json={"offer_id": shirin_offer}, headers=w.buyer
    )
    assert chosen.status_code == 204, chosen.text
    await client.post(f"{API}/requests/{request_id}/submit", headers=w.chef)

    approved = await client.post(
        f"{API}/requests/{request_id}/approve", json={"line_ids": [flour_line["id"]]}, headers=w.buyer
    )
    (order_id,) = approved.json()["order_ids"]
    order = (await client.get(f"{API}/orders/{order_id}", headers=w.buyer)).json()
    assert (order["supplier_name"], order["lines"][0]["qty_packs"], order["total"]) == ("Shirin", "5.0000", "52500.00")
    decisions = [
        ln["decision"] for ln in (await client.get(f"{API}/requests/{request_id}", headers=w.chef)).json()["lines"]
    ]
    assert decisions == ["approved", "rejected"]


async def test_return_and_reject(client: AsyncClient, world: World) -> None:
    w = world
    request_id = await _submitted(client, w, [(w.flour, "5")])
    no_comment = await client.post(f"{API}/requests/{request_id}/return", json={"comment": ""}, headers=w.buyer)
    assert no_comment.status_code == 422
    returned = await client.post(f"{API}/requests/{request_id}/return", json={"comment": "Kamroq"}, headers=w.buyer)
    assert returned.status_code == 204
    detail = (await client.get(f"{API}/requests/{request_id}", headers=w.chef)).json()
    assert detail["status"] == "DRAFT"
    assert detail["approvals"][0]["comment"] == "Kamroq"

    await client.post(f"{API}/requests/{request_id}/submit", headers=w.chef)
    assert (
        await client.post(f"{API}/requests/{request_id}/reject", json={"comment": "Kerak emas"}, headers=w.approver)
    ).status_code == 204
    assert (await client.get(f"{API}/requests/{request_id}", headers=w.chef)).json()["status"] == "REJECTED"


async def test_visibility(client: AsyncClient, world: World, admin_headers: dict[str, str]) -> None:
    w = world
    await _draft(client, w, [(w.flour, "1")])
    other_chef = await onboard(client, admin_headers, 7009, [{"role": "initiator", "store_id": w.store}])
    assert (await client.get(f"{API}/requests", headers=other_chef)).json() == []
    assert len((await client.get(f"{API}/requests", headers=w.chef)).json()) == 1
    assert len((await client.get(f"{API}/requests", headers=w.buyer)).json()) == 1
    assert (await client.get(f"{API}/orders", headers=w.chef)).status_code == 403
