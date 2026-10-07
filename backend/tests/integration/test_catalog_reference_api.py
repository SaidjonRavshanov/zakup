"""Ma'lumotnomalar: ombor → kategoriya → tovar → yetkazib beruvchi → taklif → narx tarixi → xarid kartochkasi."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import bearer, sign_in

pytestmark = pytest.mark.integration

API = "/api/v1/catalog"


async def _create(client: AsyncClient, path: str, body: dict[str, object], headers: dict[str, str]) -> str:
    response = await client.post(f"{API}{path}", json=body, headers=headers)
    assert response.status_code == 201, response.text
    created: str = response.json()["id"]
    return created


async def test_reference_data_flow(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    h = admin_headers
    kitchen = await _create(client, "/stores", {"name": "Oshxona", "address": "Toshkent"}, h)
    category = await _create(client, "/categories", {"name": "Bakaleya", "monthly_budget": "15000000"}, h)
    flour = await _create(
        client, "/products", {"name": "Un oliy nav", "base_unit": "kg", "category_id": category, "article": "U-1"}, h
    )
    supplier = await _create(
        client,
        "/suppliers",
        {
            "name": "Don Mahsulot",
            "payment_terms": "deferred",
            "deferral_days": 14,
            "lead_time_days": 2,
            "order_weekdays": [1, 4],
            "order_cutoff": "16:00",
            "contacts": {"phone": "+998901234567", "telegram": "@don"},
        },
        h,
    )

    offer = await _create(
        client,
        f"/suppliers/{supplier}/offers",
        {"product_id": flour, "pack_unit": "bag", "pack_factor": "25", "supplier_sku": "DM-25", "price": "250000"},
        h,
    )
    duplicate = await client.post(
        f"{API}/suppliers/{supplier}/offers",
        json={"product_id": flour, "pack_unit": "bag", "pack_factor": "25", "supplier_sku": "DM-25", "price": "1"},
        headers=h,
    )
    assert duplicate.json()["code"] == "duplicate_offer"

    revised = await client.put(
        f"{API}/offers/{offer}",
        json={"pack_unit": "bag", "pack_factor": "25", "supplier_sku": "DM-25", "price": "262500"},
        headers=h,
    )
    assert revised.status_code == 204, revised.text
    history = (await client.get(f"{API}/offers/{offer}/price-history", headers=h)).json()
    assert [entry["price"] for entry in history] == ["262500.0000", "250000.0000"]

    card = await client.put(
        f"{API}/purchase-cards",
        json={
            "product_id": flour,
            "store_id": kitchen,
            "mode": "auto",
            "safety_stock": "20",
            "coverage_days": 5,
            "primary_supplier_id": supplier,
        },
        headers=h,
    )
    assert card.status_code == 200, card.text

    detail = (await client.get(f"{API}/products/{flour}", headers=h)).json()
    assert detail["category_name"] == "Bakaleya"
    assert [(o["supplier_name"], o["price"], o["base_unit_price"]) for o in detail["offers"]] == [
        ("Don Mahsulot", "262500.0000", "10500.0000")
    ]
    assert [(c["store_name"], c["mode"], c["primary_supplier_name"]) for c in detail["cards"]] == [
        ("Oshxona", "auto", "Don Mahsulot")
    ]

    supplier_detail = (await client.get(f"{API}/suppliers/{supplier}", headers=h)).json()
    assert supplier_detail["order_weekdays"] == [1, 4]
    assert supplier_detail["order_cutoff"] == "16:00:00"
    assert supplier_detail["contacts"]["telegram"] == "@don"
    assert len(supplier_detail["offers"]) == 1

    listed = (await client.get(f"{API}/products", params={"search": "un"}, headers=h)).json()
    assert [(p["name"], p["offers_count"]) for p in listed] == [("Un oliy nav", 1)]


async def test_price_history_keeps_every_change(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    h = admin_headers
    product = await _create(client, "/products", {"name": "Shakar", "base_unit": "kg"}, h)
    supplier = await _create(client, "/suppliers", {"name": "Shirin", "payment_terms": "prepay"}, h)
    offer = await _create(
        client,
        f"/suppliers/{supplier}/offers",
        {"product_id": product, "pack_unit": "bag", "pack_factor": "50", "price": "600000"},
        h,
    )
    body = {"pack_unit": "bag", "pack_factor": "50"}
    # Kelajakdagi sana taqiqlangan (darhol amal qilib qolardi)
    future = await client.put(
        f"{API}/offers/{offer}", json={**body, "price": "700000", "price_valid_from": "2099-01-01"}, headers=h
    )
    assert future.json()["code"] == "invalid_offer"
    for price in ("610000", "640000"):  # sana ko'rsatilmasa — bugun
        response = await client.put(f"{API}/offers/{offer}", json={**body, "price": price}, headers=h)
        assert response.status_code == 204, response.text

    history = (await client.get(f"{API}/offers/{offer}/price-history", headers=h)).json()
    assert [(e["price"], e["source"]) for e in history] == [
        ("640000.0000", "manual"),
        ("610000.0000", "manual"),
        ("600000.0000", "manual"),
    ]

    backdated = await client.put(
        f"{API}/offers/{offer}", json={**body, "price": "1", "price_valid_from": "2020-01-01"}, headers=h
    )
    assert backdated.json()["code"] == "invalid_offer"


async def test_auto_card_without_supplier_is_rejected(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    h = admin_headers
    store = await _create(client, "/stores", {"name": "Bar"}, h)
    product = await _create(client, "/products", {"name": "Limon", "base_unit": "kg"}, h)
    response = await client.put(
        f"{API}/purchase-cards", json={"product_id": product, "store_id": store, "mode": "auto"}, headers=h
    )
    assert (response.status_code, response.json()["code"]) == (422, "invalid_purchase_card")


async def test_only_admin_manages_stores_and_buyer_manages_products(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await sign_in(client, 9009)
    listed = await client.get("/api/v1/identity/users", params={"status": "pending"}, headers=admin_headers)
    user_id = next(u["id"] for u in listed.json() if u["telegram_id"] == 9009)
    await client.post(f"/api/v1/identity/users/{user_id}/activate", headers=admin_headers)
    await client.put(
        f"/api/v1/identity/users/{user_id}/roles", json={"grants": [{"role": "buyer"}]}, headers=admin_headers
    )
    buyer = bearer((await sign_in(client, 9009)).json())

    assert (await client.post(f"{API}/stores", json={"name": "X"}, headers=buyer)).status_code == 403
    product = await client.post(f"{API}/products", json={"name": "Tuz", "base_unit": "kg"}, headers=buyer)
    assert product.status_code == 201
    assert (await client.get(f"{API}/stores", headers=buyer)).status_code == 200


async def test_supplier_revise_and_archive(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    h = admin_headers
    supplier = await _create(client, "/suppliers", {"name": "Eski nom", "payment_terms": "prepay"}, h)
    response = await client.put(
        f"{API}/suppliers/{supplier}",
        json={"name": "Yangi nom", "payment_terms": "on_delivery", "lead_time_days": 3},
        headers=h,
    )
    assert response.status_code == 204, response.text
    assert (await client.post(f"{API}/suppliers/{supplier}/archive", headers=h)).status_code == 204

    active = (await client.get(f"{API}/suppliers", headers=h)).json()
    assert supplier not in [s["id"] for s in active]
    archived = (await client.get(f"{API}/suppliers", params={"include_archived": True}, headers=h)).json()
    assert [(s["name"], s["archived"]) for s in archived] == [("Yangi nom", True)]
