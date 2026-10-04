"""planning modulining public interfeysi (ARCHITECTURE §3.1).

- `PlanningIngest` — integration_iiko yozadi: qoldiq snapshot'i va kunlik sarf.
- `DemandQueries` — procurement o'qiydi: o'rtacha sarf + qoldiq (avto-zayavka uchun).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from zakup.modules.planning.domain.demand import DemandInputs, DemandResult, average_daily, calculate

__all__ = ["DemandInputs", "DemandQueries", "DemandResult", "DemandStats", "PlanningIngest", "calculate"]


@dataclass(frozen=True, slots=True)
class StockRow:
    store_id: UUID
    product_id: UUID
    qty: Decimal


@dataclass(frozen=True, slots=True)
class ConsumptionRow:
    store_id: UUID
    product_id: UUID
    day: date
    qty: Decimal


class PlanningStore(Protocol):
    async def replace_stock(self, store_ids: set[UUID], rows: list[StockRow], *, taken_at: datetime) -> None: ...

    async def replace_consumption(
        self, store_ids: set[UUID], rows: list[ConsumptionRow], *, date_from: date, date_to: date
    ) -> None:
        """[date_from, date_to) oralig'idagi shu omborlar sarfi to'liq almashtiriladi (iiko'da tuzatishlar bo'ladi)."""

    async def consumption_totals(
        self, store_id: UUID, product_ids: Iterable[UUID], *, date_from: date, date_to: date
    ) -> dict[UUID, Decimal]: ...

    async def first_day(self, store_id: UUID) -> date | None:
        """Shu ombor bo'yicha sarf tarixi qachondan bor."""

    async def stock(self, store_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, tuple[Decimal, datetime]]: ...

    async def has_history(self) -> bool: ...


class PlanningIngest:
    def __init__(self, store: PlanningStore) -> None:
        self._store = store

    async def replace_stock(self, store_ids: set[UUID], rows: list[StockRow], *, taken_at: datetime) -> None:
        await self._store.replace_stock(store_ids, rows, taken_at=taken_at)

    async def replace_consumption(
        self, store_ids: set[UUID], rows: list[ConsumptionRow], *, date_from: date, date_to: date
    ) -> None:
        await self._store.replace_consumption(store_ids, rows, date_from=date_from, date_to=date_to)


@dataclass(frozen=True, slots=True)
class DemandStats:
    avg_daily: Decimal
    days_observed: int  # 0 — sarf tarixi yo'q (hisob qilib bo'lmaydi)
    window_days: int
    stock: Decimal | None  # None — qoldiq noma'lum
    stock_at: datetime | None


class DemandQueries:
    def __init__(self, store: PlanningStore, *, window_days: int = 28) -> None:
        self._store = store
        self._window = window_days

    async def has_history(self) -> bool:
        """Sarf tarixi umuman bormi (yo'q — birinchi sinxronda 28 kun olinadi)."""
        return await self._store.has_history()

    async def stats(self, store_id: UUID, product_ids: Iterable[UUID], *, today: date) -> dict[UUID, DemandStats]:
        ids = list(product_ids)
        totals = await self._store.consumption_totals(
            store_id, ids, date_from=today - timedelta(days=self._window), date_to=today
        )
        first = await self._store.first_day(store_id)
        stock = await self._store.stock(store_id, ids)
        result = {}
        for product_id in ids:
            avg, days = average_daily(
                totals.get(product_id, Decimal(0)), window_days=self._window, first_day=first, today=today
            )
            qty, at = stock.get(product_id, (None, None))
            result[product_id] = DemandStats(
                avg_daily=avg, days_observed=days, window_days=self._window, stock=qty, stock_at=at
            )
        return result
