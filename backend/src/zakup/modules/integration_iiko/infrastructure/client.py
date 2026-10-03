"""iikoServer REST API (iikoRMS 9.x) klienti.

Sessiya: GET /api/auth?login=..&pass=sha1(parol) → token; har so'rovda ?key=token; oxirida GET /api/logout.
Litsenziya serverga bitta API-sessiyaga ruxsat beradi → sessiya oldidan blok (ADR-05), logout — har doim.
"""

import asyncio
import hashlib
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import date
from typing import TypeVar

import httpx
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from zakup.modules.integration_iiko.application.ports import IikoReader, ServerInfo
from zakup.modules.integration_iiko.domain.models import (
    IikoDepartment,
    IikoIncomingInvoice,
    IikoProduct,
    IikoProductGroup,
    IikoStore,
    IikoSupplier,
    IikoUnit,
)
from zakup.modules.integration_iiko.infrastructure import parsers
from zakup.settings import IikoServerSettings
from zakup.shared_kernel.errors import DomainError, NotFoundError

log = structlog.get_logger()
T = TypeVar("T")
RETRIES = 3


class IikoUnavailableError(DomainError):
    code = "iiko_unavailable"


class IikoAuthError(DomainError):
    code = "iiko_auth"


SessionLock = Callable[[str], AbstractAsyncContextManager[None]]


class PgAdvisoryLock:
    """Process'lar orasida "serverga bitta sessiya": PostgreSQL advisory lock (Redis'siz)."""

    def __init__(self, engine: AsyncEngine, wait_s: float) -> None:
        self._engine = engine
        self._wait_s = wait_s

    @asynccontextmanager
    async def __call__(self, name: str) -> AsyncIterator[None]:
        key = f"iiko:{name}"
        async with self._engine.connect() as conn:
            deadline = asyncio.get_running_loop().time() + self._wait_s
            while not await conn.scalar(text("SELECT pg_try_advisory_lock(hashtext(:k))"), {"k": key}):
                if asyncio.get_running_loop().time() > deadline:
                    raise IikoUnavailableError("iiko.session_busy", server=name)
                await asyncio.sleep(1)
            try:
                yield
            finally:
                await conn.scalar(text("SELECT pg_advisory_unlock(hashtext(:k))"), {"k": key})


class _HttpReader:
    def __init__(self, http: httpx.AsyncClient, key: str) -> None:
        self._http = http
        self._key = key

    async def _get(self, path: str, parse: Callable[[bytes], T], **params: str) -> T:
        for attempt in range(1, RETRIES + 1):
            try:
                response = await self._http.get(path, params={**params, "key": self._key})
                if response.status_code < 500:  # noqa: PLR2004
                    break
            except httpx.TransportError as exc:
                if attempt == RETRIES:
                    raise IikoUnavailableError("iiko.unavailable") from exc
            await asyncio.sleep(attempt)
        if response.status_code != 200:  # noqa: PLR2004
            log.warning("iiko_bad_status", path=path, status=response.status_code, body=response.text[:300])
            raise IikoUnavailableError("iiko.bad_status", status=response.status_code)
        return parse(response.content)

    async def departments(self) -> list[IikoDepartment]:
        return await self._get("/corporation/departments", parsers.parse_departments)

    async def stores(self) -> list[IikoStore]:
        return await self._get("/corporation/stores", parsers.parse_stores)

    async def units(self) -> list[IikoUnit]:
        return await self._get("/v2/entities/list", parsers.parse_units, rootType="MeasureUnit")

    async def product_groups(self) -> list[IikoProductGroup]:
        return await self._get("/v2/entities/products/group/list", parsers.parse_product_groups)

    async def products(self) -> list[IikoProduct]:
        return await self._get("/v2/entities/products/list", parsers.parse_products)

    async def suppliers(self) -> list[IikoSupplier]:
        return await self._get("/suppliers", parsers.parse_suppliers)

    async def incoming_invoices(self, date_from: date, date_to: date) -> list[IikoIncomingInvoice]:
        return await self._get(
            "/documents/export/incomingInvoice",
            parsers.parse_incoming_invoices,
            **{"from": date_from.isoformat(), "to": date_to.isoformat()},
        )


class HttpIikoGateway:
    def __init__(
        self,
        servers: list[IikoServerSettings],
        lock: SessionLock,
        *,
        timeout_s: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._servers = {server.code: server for server in servers}
        self._lock = lock
        self._timeout = timeout_s
        self._transport = transport  # testda — fake iiko ASGI ilovasi

    def servers(self) -> list[ServerInfo]:
        return [ServerInfo(s.code, s.name, s.department_code) for s in self._servers.values()]

    @asynccontextmanager
    async def session(self, server_code: str) -> AsyncIterator[IikoReader]:
        config = self._servers.get(server_code)
        if config is None:
            raise NotFoundError("iiko.server_not_found")
        base_url = str(config.base_url).rstrip("/") + "/api"
        async with (
            self._lock(server_code),
            httpx.AsyncClient(base_url=base_url, timeout=self._timeout, transport=self._transport) as http,
        ):
            key = await self._auth(http, config)
            log.info("iiko_session_opened", server=server_code)
            try:
                yield _HttpReader(http, key)
            finally:
                await self._logout(http, key, server_code)

    @staticmethod
    async def _auth(http: httpx.AsyncClient, config: IikoServerSettings) -> str:
        password_hash = hashlib.sha1(config.password.get_secret_value().encode()).hexdigest()  # noqa: S324 — iiko talabi
        try:
            response = await http.get("/auth", params={"login": config.login, "pass": password_hash})
        except httpx.TransportError as exc:
            raise IikoUnavailableError("iiko.unavailable") from exc
        token = response.text.strip()
        if response.status_code != 200 or not token or len(token) > 100:  # noqa: PLR2004
            log.warning("iiko_auth_failed", server=config.code, status=response.status_code, body=response.text[:200])
            raise IikoAuthError("iiko.auth_failed", server=config.code)
        return token

    @staticmethod
    async def _logout(http: httpx.AsyncClient, key: str, server_code: str) -> None:
        try:
            await http.get("/logout", params={"key": key})
            log.info("iiko_session_closed", server=server_code)
        except httpx.HTTPError:
            # Logout bo'lmasa, sessiya iiko'da muddati bilan yopiladi — lekin litsenziya band qoladi: ogohlantiramiz
            log.exception("iiko_logout_failed", server=server_code)
