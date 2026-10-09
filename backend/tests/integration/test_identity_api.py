import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient

from tests.integration.conftest import ADMIN_TELEGRAM_ID, BOT_TOKEN, bearer, sign_in

pytestmark = pytest.mark.integration

USERS = "/api/v1/identity/users"


def _signed_init_data(telegram_id: int, first_name: str) -> str:
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "AAH",
        "user": json.dumps({"id": telegram_id, "first_name": first_name, "language_code": "ru"}),
    }
    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


async def _pending_user_id(client: AsyncClient, admin_headers: dict[str, str], telegram_id: int) -> str:
    listed = await client.get(USERS, params={"status": "pending"}, headers=admin_headers)
    return next(u["id"] for u in listed.json() if u["telegram_id"] == telegram_id)


async def _onboard(
    client: AsyncClient, admin_headers: dict[str, str], telegram_id: int, grants: list[dict[str, str | None]]
) -> dict[str, str]:
    """Yangi foydalanuvchi: kiradi → admin faollashtiradi va rol beradi → qayta kiradi."""
    assert (await sign_in(client, telegram_id)).status_code == 403
    user_id = await _pending_user_id(client, admin_headers, telegram_id)
    assert (await client.post(f"{USERS}/{user_id}/activate", headers=admin_headers)).status_code == 204
    roles = await client.put(f"{USERS}/{user_id}/roles", json={"grants": grants}, headers=admin_headers)
    assert roles.status_code == 204, roles.text
    session = await sign_in(client, telegram_id)
    assert session.status_code == 200, session.text
    result: dict[str, str] = session.json()
    return result


async def test_unknown_user_waits_for_activation(client: AsyncClient) -> None:
    response = await sign_in(client, 2002, "Begona")
    assert response.status_code == 403
    assert response.json()["code"] == "account_pending"


async def test_telegram_sign_in_checks_signature(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    init_data = _signed_init_data(3003, "Shef")
    pending = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    assert pending.json()["code"] == "account_pending"

    forged = init_data.replace("Shef", "Hacker")
    response = await client.post("/api/v1/auth/telegram", json={"init_data": forged})
    assert response.json()["code"] == "invalid_init_data"

    listed = await client.get(USERS, params={"status": "pending"}, headers=admin_headers)
    assert [(u["telegram_id"], u["locale"]) for u in listed.json()] == [(3003, "ru")]


async def test_admin_onboards_user_and_me_shows_roles(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    store = await client.post("/api/v1/catalog/stores", json={"name": "Oshxona"}, headers=admin_headers)
    store_id = store.json()["id"]
    session = await _onboard(
        client, admin_headers, 4004, [{"role": "buyer"}, {"role": "storekeeper", "store_id": store_id}]
    )

    me = (await client.get("/api/v1/me", headers=bearer(session))).json()
    assert me["telegram_id"] == 4004
    assert me["is_active"] is True
    assert me["grants"] == [{"role": "buyer", "store_id": None}, {"role": "storekeeper", "store_id": store_id}]

    assert (await client.patch("/api/v1/me", json={"locale": "ru"}, headers=bearer(session))).status_code == 204
    assert (await client.get("/api/v1/me", headers=bearer(session))).json()["locale"] == "ru"


async def test_roles_are_enforced(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    initiator = bearer(await _onboard(client, admin_headers, 5005, [{"role": "initiator"}]))
    buyer = bearer(await _onboard(client, admin_headers, 5006, [{"role": "buyer"}]))
    body = {"name": "Go'sht", "payment_terms": "prepay"}

    denied = await client.post("/api/v1/catalog/suppliers", json=body, headers=initiator)
    assert (denied.status_code, denied.json()["code"]) == (403, "permission_denied")
    assert (await client.post("/api/v1/catalog/suppliers", json=body, headers=buyer)).status_code == 201
    assert (await client.get(USERS, headers=buyer)).status_code == 403


async def test_refresh_rotation_and_reuse_detection(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    session = await _onboard(client, admin_headers, 6006, [{"role": "buyer"}])
    old_refresh = session["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Eski token qayta ishlatildi → o'g'irlik deb hisoblanadi, barcha sessiyalar yopiladi
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})).status_code == 401


async def test_deactivated_user_cannot_refresh(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    session = await _onboard(client, admin_headers, 7007, [{"role": "buyer"}])
    user_id = (await client.get("/api/v1/me", headers=bearer(session))).json()["id"]

    assert (await client.post(f"{USERS}/{user_id}/deactivate", headers=admin_headers)).status_code == 204
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert response.status_code == 401
    assert (await sign_in(client, 7007)).json()["code"] == "account_pending"


async def test_admin_cannot_lock_themselves_out(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    me = (await client.get("/api/v1/me", headers=admin_headers)).json()
    response = await client.put(
        f"{USERS}/{me['id']}/roles", json={"grants": [{"role": "buyer"}]}, headers=admin_headers
    )
    assert (response.status_code, response.json()["code"]) == (422, "self_lockout")


async def test_logout_revokes_refresh_token(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    session = (await sign_in(client, 1001)).json()
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": session["refresh_token"]})
    ).status_code == 204
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert response.status_code == 401


async def test_role_for_unknown_store_is_rejected(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    await sign_in(client, 8008)
    user_id = await _pending_user_id(client, admin_headers, 8008)
    grants = [{"role": "storekeeper", "store_id": "0192a000-0000-7000-8000-000000000001"}]
    response = await client.put(f"{USERS}/{user_id}/roles", json={"grants": grants}, headers=admin_headers)
    assert (response.status_code, response.json()["code"]) == (422, "invalid_user")


async def test_browser_handoff_code_is_single_use(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    """Telegram (macOS) → tizim brauzeri: bir martalik kod oddiy sessiyaga almashadi, ikkinchi marta — yo'q."""
    assert (await client.post("/api/v1/auth/handoff")).status_code == 401
    code = (await client.post("/api/v1/auth/handoff", headers=admin_headers)).json()["code"]

    browser = await client.post("/api/v1/auth/refresh", json={"refresh_token": code})
    assert browser.status_code == 200, browser.text
    me = await client.get("/api/v1/me", headers=bearer(browser.json()))
    assert me.json()["telegram_id"] == ADMIN_TELEGRAM_ID

    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": code})).status_code == 401
