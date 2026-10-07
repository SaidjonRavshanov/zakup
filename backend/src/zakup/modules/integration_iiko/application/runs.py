"""Sinxronizatsiya navbati: admin so'raydi (API) → worker bajaradi (API iiko'ga chiqmaydi, ADR-05).

iiko sessiyasi imkon qadar qisqa: avval kerakli hamma narsa xotiraga yuklanadi (Snapshot), sessiya yopiladi,
keyin bazaga yoziladi. Litsenziya bitta sessiyaga ruxsat beradi — boshqa tizimlar (hisobotlar) kutib qolmasin.
"""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

import structlog

from zakup.modules.integration_iiko.application.planning import ImportConsumption, ImportStock
from zakup.modules.integration_iiko.application.ports import (
    IikoGateway,
    IikoReader,
    ServerInfo,
    SyncKind,
    SyncRun,
    SyncRunItem,
    SyncRunReader,
    SyncRuns,
)
from zakup.modules.integration_iiko.application.sync import ImportPurchasePrices, SyncReferences
from zakup.modules.integration_iiko.domain.models import (
    IikoDepartment,
    IikoIncomingInvoice,
    IikoMovement,
    IikoProduct,
    IikoProductGroup,
    IikoStockBalance,
    IikoStore,
    IikoSupplier,
    IikoUnit,
)
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, business_today, utc_now
from zakup.shared_kernel.errors import ConflictError, DomainError, NotFoundError

log = structlog.get_logger()
TASHKENT_OFFSET = timedelta(hours=5)  # UTC+5, DST yo'q
DEFAULT_PRICE_DAYS = 30
MAX_PRICE_DAYS = 120
DEFAULT_CONSUMPTION_DAYS = 3  # kundalik: oxirgi kunlar qayta olinadi (iiko'da kechikkan tuzatishlar)
MAX_CONSUMPTION_DAYS = 31  # OLAP bo'laklari xotirada: worker 256 MB (1 GB server) — bir oydan oshmasin
BACKFILL_CONSUMPTION_DAYS = 28  # birinchi marta — o'rtacha sarf oynasi
CONSUMPTION_CHUNK_DAYS = 7  # OLAP javobi katta: haftalik bo'laklar (Sebzar: ~30 ming qator / hafta)


class InvalidSyncRequestError(DomainError):
    code = "invalid_sync_request"


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Sessiya davomida yuklangan ma'lumot — sessiyadan keyin IikoReader sifatida o'qiladi."""

    departments_: list[IikoDepartment]
    stores_: list[IikoStore]
    units_: list[IikoUnit]
    groups_: list[IikoProductGroup]
    products_: list[IikoProduct]
    suppliers_: list[IikoSupplier]
    invoices_: list[IikoIncomingInvoice]
    stock_: list[IikoStockBalance] = field(default_factory=list)
    movements_: list[IikoMovement] = field(default_factory=list)

    @classmethod
    async def fetch(
        cls, reader: IikoReader, kind: SyncKind, period: tuple[date, date] | None, at: datetime
    ) -> "Snapshot":
        if kind is SyncKind.REFERENCES:
            return cls(
                await reader.departments(),
                await reader.stores(),
                await reader.units(),
                await reader.product_groups(),
                await reader.products(),
                await reader.suppliers(),
                [],
            )
        if kind is SyncKind.STOCK:
            return cls([], [], [], [], [], [], [], stock_=await reader.stock_balances(at))
        assert period is not None
        if kind is SyncKind.CONSUMPTION:
            movements: list[IikoMovement] = []
            start = period[0]
            while start < period[1]:
                end = min(start + timedelta(days=CONSUMPTION_CHUNK_DAYS), period[1])
                movements.extend(await reader.movements(start, end))
                start = end
            return cls([], [], [], [], [], [], [], movements_=movements)
        return cls([], [], [], [], [], [], await reader.incoming_invoices(*period))

    async def departments(self) -> list[IikoDepartment]:
        return self.departments_

    async def stores(self) -> list[IikoStore]:
        return self.stores_

    async def units(self) -> list[IikoUnit]:
        return self.units_

    async def product_groups(self) -> list[IikoProductGroup]:
        return self.groups_

    async def products(self) -> list[IikoProduct]:
        return self.products_

    async def suppliers(self) -> list[IikoSupplier]:
        return self.suppliers_

    async def incoming_invoices(self, date_from: date, date_to: date) -> list[IikoIncomingInvoice]:
        return [i for i in self.invoices_ if date_from <= i.incoming_date <= date_to]

    async def stock_balances(self, at: datetime) -> list[IikoStockBalance]:
        return self.stock_

    async def movements(self, date_from: date, date_to: date) -> list[IikoMovement]:
        return [m for m in self.movements_ if date_from <= m.day < date_to]


class RequestSync:
    def __init__(self, gateway: IikoGateway, runs: SyncRuns, commit: Callable[[], Awaitable[None]]) -> None:
        self._gateway = gateway
        self._runs = runs
        self._commit = commit

    async def __call__(self, actor: Principal, *, server_code: str, kind: SyncKind, days: int | None = None) -> UUID:
        actor.require(Role.ADMIN)
        if server_code not in {s.code for s in self._gateway.servers()}:
            raise NotFoundError("iiko.server_not_found")
        params: dict[str, Any] = {}
        if kind in DAY_LIMITS:
            default, maximum = DAY_LIMITS[kind]
            days = days or default
            if not 1 <= days <= maximum:
                raise InvalidSyncRequestError("iiko.days_range", max=maximum)
            params["days"] = days
        if await self._runs.has_pending(server_code, kind):
            raise ConflictError("iiko.sync_pending")
        run_id = await self._runs.enqueue(server_code=server_code, kind=kind, params=params, requested_by=actor.user_id)
        await self._commit()
        return run_id


DAY_LIMITS = {
    SyncKind.PURCHASE_PRICES: (DEFAULT_PRICE_DAYS, MAX_PRICE_DAYS),
    SyncKind.CONSUMPTION: (DEFAULT_CONSUMPTION_DAYS, MAX_CONSUMPTION_DAYS),
}


class ScheduleDailySyncs:
    """Har kuni ertalab (worker): har bir serverga narxlar + sarf + qoldiq — avto-zayavkadan oldin.

    Sarf tarixi hali yo'q bo'lsa — birinchi marta 28 kun (o'rtacha sarf oynasi) olinadi.
    """

    def __init__(self, gateway: IikoGateway, runs: SyncRuns, commit: Callable[[], Awaitable[None]]) -> None:
        self._gateway = gateway
        self._runs = runs
        self._commit = commit

    async def __call__(self, *, backfill: bool) -> int:
        queued = 0
        consumption_days = BACKFILL_CONSUMPTION_DAYS if backfill else DEFAULT_CONSUMPTION_DAYS
        plan: tuple[tuple[SyncKind, dict[str, Any]], ...] = (
            (SyncKind.PURCHASE_PRICES, {"days": 2}),
            (SyncKind.CONSUMPTION, {"days": consumption_days}),
            (SyncKind.STOCK, {}),
        )
        for server in self._gateway.servers():
            for kind, params in plan:
                if await self._runs.has_pending(server.code, kind):
                    continue
                await self._runs.enqueue(server_code=server.code, kind=kind, params=params, requested_by=None)
                queued += 1
        await self._commit()
        return queued


@dataclass(frozen=True, slots=True)
class SyncScope:
    """Bitta tranzaksiya: runs + sinxronizatorlar bitta sessiyani ulashadi."""

    runs: SyncRuns
    references: SyncReferences
    prices: ImportPurchasePrices
    stock: ImportStock
    consumption: ImportConsumption
    commit: Callable[[], Awaitable[None]]


class ScopeFactory(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[SyncScope]: ...



def _public_error(exc: Exception) -> str:
    """Foydalanuvchiga ko'rinadigan xato: domen xatosi — kaliti; boshqasi (SQL, parametrlar) — faqat turi, tafsilot logda."""
    if isinstance(exc, DomainError):
        return f"{type(exc).__name__}: {exc}"[:500]
    return f"{type(exc).__name__} (tafsilot — worker logida)"

class RunNextSync:
    """Worker qadami: navbatdan bitta ishni oladi va bajaradi. True — ish bor edi."""

    def __init__(self, gateway: IikoGateway, scope: ScopeFactory, clock: Clock = utc_now) -> None:
        self._gateway = gateway
        self._scope = scope
        self._clock = clock

    async def __call__(self) -> bool:
        async with self._scope() as scope:
            run = await scope.runs.claim_next()
            await scope.commit()
        if run is None:
            return False

        log.info("iiko_sync_started", run_id=str(run.id), server=run.server_code, kind=run.kind)
        try:
            stats = await self._execute(run)
        except Exception as exc:  # worker yiqilmasin: xato run'ga yoziladi
            log.exception("iiko_sync_failed", run_id=str(run.id))
            await self._finish(run.id, {}, _public_error(exc))
        else:
            log.info("iiko_sync_done", run_id=str(run.id), **stats)
            await self._finish(run.id, stats, None)
        return True

    async def _execute(self, run: SyncRun) -> dict[str, int]:
        now = self._clock()
        today = business_today(self._clock)
        period = None
        if run.kind is SyncKind.PURCHASE_PRICES:
            period = (today - timedelta(days=int(run.params.get("days", DEFAULT_PRICE_DAYS))), today)
        elif run.kind is SyncKind.CONSUMPTION:
            # [from, today): bugungi to'liq bo'lmagan kun olinmaydi
            period = (today - timedelta(days=int(run.params.get("days", DEFAULT_CONSUMPTION_DAYS))), today)
        server_now = (now + TASHKENT_OFFSET).replace(tzinfo=None)  # iiko serveri vaqti — balance timestamp
        async with self._gateway.session(run.server_code) as reader:
            snapshot = await Snapshot.fetch(reader, run.kind, period, server_now)
        async with self._scope() as scope:
            if run.kind is SyncKind.REFERENCES:
                stats = await scope.references(run.server_code, snapshot)
            elif run.kind is SyncKind.STOCK:
                stats = await scope.stock(run.server_code, snapshot, now)
            elif run.kind is SyncKind.CONSUMPTION:
                assert period is not None
                stats = await scope.consumption(run.server_code, snapshot, *period)
            else:
                assert period is not None
                stats = await scope.prices(run.server_code, snapshot, *period)
            await scope.commit()
        return stats

    async def _finish(self, run_id: UUID, stats: dict[str, int], error: str | None) -> None:
        async with self._scope() as scope:
            await scope.runs.finish(run_id, stats=stats, error=error)
            await scope.commit()


class ListSyncRuns:
    def __init__(self, gateway: IikoGateway, reader: SyncRunReader) -> None:
        self._gateway = gateway
        self._reader = reader

    async def __call__(self, actor: Principal, *, limit: int = 50) -> tuple[list[ServerInfo], list[SyncRunItem]]:
        actor.require(Role.ADMIN, Role.BUYER, Role.AUDITOR)
        return self._gateway.servers(), await self._reader.recent(limit=max(1, min(limit, 200)))
