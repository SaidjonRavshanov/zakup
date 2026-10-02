import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import TEST_DB_URL

pytestmark = pytest.mark.integration


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


async def test_register_and_list_supplier_writes_outbox(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/catalog/suppliers",
        json={"name": "Sutli Vodiy", "inn": "305123456", "payment_terms": "deferred", "deferral_days": 14},
    )
    assert created.status_code == 201, created.text

    listed = await client.get("/api/v1/catalog/suppliers", params={"search": "sutli"})
    assert [s["name"] for s in listed.json()] == ["Sutli Vodiy"]

    # Event biznes yozuvi bilan bitta tranzaksiyada outbox'ga tushgan (ADR-04)
    engine = create_async_engine(TEST_DB_URL)
    async with engine.connect() as conn:
        events = (await conn.execute(text("SELECT event_type FROM platform.outbox"))).scalars().all()
    await engine.dispose()
    assert events == ["catalog.supplier_registered"]


async def test_duplicate_inn_returns_422(client: AsyncClient) -> None:
    body = {"name": "A", "inn": "305123456", "payment_terms": "prepay"}
    assert (await client.post("/api/v1/catalog/suppliers", json=body)).status_code == 201
    response = await client.post("/api/v1/catalog/suppliers", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "duplicate_inn"


async def test_domain_validation_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/catalog/suppliers", json={"name": "A", "inn": "123", "payment_terms": "prepay"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_supplier"


@pytest.mark.parametrize(
    ("accept_language", "expected"),
    [
        ("ru-RU,ru;q=0.9", "Поставщик с ИНН 305123456 уже существует"),
        ("uz", "STIR 305123456 bilan yetkazib beruvchi allaqachon bor"),
        (None, "STIR 305123456 bilan yetkazib beruvchi allaqachon bor"),
    ],
)
async def test_error_message_follows_accept_language(
    client: AsyncClient, accept_language: str | None, expected: str
) -> None:
    body = {"name": "A", "inn": "305123456", "payment_terms": "prepay"}
    await client.post("/api/v1/catalog/suppliers", json=body)
    headers = {"Accept-Language": accept_language} if accept_language else {}
    response = await client.post("/api/v1/catalog/suppliers", json=body, headers=headers)
    assert response.json() == {"code": "duplicate_inn", "message": expected}


async def test_request_validation_is_localized(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/catalog/suppliers", json={"payment_terms": "barter"}, headers={"Accept-Language": "ru"}
    )
    payload = response.json()
    assert response.status_code == 422
    assert payload["code"] == "validation_error"
    assert payload["message"] == "Некорректные данные запроса"
    assert {tuple(field["loc"]) for field in payload["fields"]} == {("body", "name"), ("body", "payment_terms")}
