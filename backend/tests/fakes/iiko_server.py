"""Soxta iikoServer (iikoRMS 9.2 javob formatlari) — testlar va lokal ishlab chiqish uchun.

Javoblar papkadagi fayllardan beriladi: tests/fixtures/iiko (kichik, qo'lda) yoki haqiqiy namunalar
(lokal: `ZAKUP_FAKE_IIKO_DIR=<papka> uvicorn --factory tests.fakes.iiko_server:app_from_env --port 8090`).

Sessiyalar kuzatiladi: bir vaqtdagi maksimal soni va yopilmay qolganlari — "serverga bitta sessiya" testlari uchun.
"""

import hashlib
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "iiko"

_FILES = {
    "/resto/api/v2/entities/list": ("units.json", "application/json"),
    "/resto/api/v2/entities/products/group/list": ("product_groups.json", "application/json"),
    "/resto/api/v2/entities/products/list": ("products.json", "application/json"),
    "/resto/api/corporation/stores": ("stores.xml", "application/xml"),
    "/resto/api/corporation/departments": ("departments.xml", "application/xml"),
    "/resto/api/suppliers": ("suppliers.xml", "application/xml"),
    "/resto/api/documents/export/incomingInvoice": ("incoming_invoices.xml", "application/xml"),
}


@dataclass
class FakeIikoState:
    login: str = "zakup"
    password: str = "secret"
    active: set[str] = field(default_factory=set)
    peak_sessions: int = 0
    opened: int = 0
    requests: list[str] = field(default_factory=list)


def create_fake_iiko(data_dir: Path = FIXTURES, state: FakeIikoState | None = None) -> FastAPI:
    app = FastAPI(title="Fake iikoServer")
    app.state.iiko = state = state or FakeIikoState()

    @app.get("/resto/api/auth")
    async def auth(login: str, password_hash: str = Query(alias="pass")) -> Response:
        expected = hashlib.sha1(state.password.encode()).hexdigest()  # noqa: S324 — iiko formati
        if login != state.login or password_hash != expected:
            return Response("Неверный логин или пароль", status_code=401, media_type="text/plain")
        key = secrets.token_hex(16)
        state.active.add(key)
        state.opened += 1
        state.peak_sessions = max(state.peak_sessions, len(state.active))
        return Response(key, media_type="text/plain")

    @app.get("/resto/api/logout")
    async def logout(key: str) -> Response:
        state.active.discard(key)
        return Response("", media_type="text/plain")

    def make_handler(filename: str, media_type: str, path: str):  # type: ignore[no-untyped-def]
        async def handler(key: str) -> Response:
            if key not in state.active:
                raise HTTPException(401, "Token is expired or invalid")
            state.requests.append(path)
            return Response((data_dir / filename).read_bytes(), media_type=f"{media_type};charset=UTF-8")

        return handler

    for path, (filename, media_type) in _FILES.items():
        app.add_api_route(path, make_handler(filename, media_type, path), methods=["GET"])
    return app


def app_from_env() -> FastAPI:
    """Lokal dev: haqiqiy namunalar papkasi bilan; login/parol — ZAKUP_FAKE_IIKO_LOGIN / _PASSWORD."""
    state = FakeIikoState(
        login=os.environ.get("ZAKUP_FAKE_IIKO_LOGIN", "zakup"),
        password=os.environ.get("ZAKUP_FAKE_IIKO_PASSWORD", "secret"),
    )
    return create_fake_iiko(Path(os.environ.get("ZAKUP_FAKE_IIKO_DIR", str(FIXTURES))), state)
