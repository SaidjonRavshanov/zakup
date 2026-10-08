"""Hisobotlar (WORKFLOW B13 nazorat, B14 tahlil) — faqat o'qish.

analytics — read-model qatlami: boshqa modullarning jadvallarini SQL orqali O'QIYDI (yozmaydi, ularning kodini
import qilmaydi — ARCHITECTURE §3, "analytics: read-model'lar"). Ruxsat va davr — shu yerda.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol
from uuid import UUID

from zakup.modules.analytics.domain.rating import change_pct, score_penalties, supplier_score
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, business_today, utc_now
from zakup.shared_kernel.errors import DomainError

VIEWERS = (Role.BUYER, Role.APPROVER, Role.ADMIN, Role.AUDITOR, Role.ACCOUNTANT)
CONTROLLERS = (Role.AUDITOR, Role.APPROVER, Role.ADMIN)
MAX_PERIOD_DAYS = 366
DEFAULT_PERIOD_DAYS = 30


class InvalidReportError(DomainError):
    code = "invalid_report"


@dataclass(frozen=True, slots=True)
class Period:
    date_from: date  # [from, to)
    date_to: date

    @property
    def previous(self) -> "Period":
        """Shu uzunlikdagi oldingi davr (taqqoslash uchun)."""
        length = self.date_to - self.date_from
        return Period(self.date_from - length, self.date_from)


@dataclass(frozen=True, slots=True)
class Summary:
    period: Period
    purchases: Decimal
    purchases_prev: Decimal
    receipts: int
    savings: Decimal  # buyurtmadagidan arzonroq qabul qilingan
    overpay: Decimal  # buyurtmadagidan qimmatroq
    defect_loss: Decimal
    price_change_pct: Decimal | None  # bir xil tovarlar bo'yicha o'rtacha narx o'zgarishi (oldingi davrga)
    pending_requests: int
    auto_drafts: int
    orders_in_transit: int
    arriving_today: int
    open_disputes: int
    debt: Decimal
    overdue: Decimal


@dataclass(frozen=True, slots=True)
class SupplierRating:
    supplier_id: UUID
    supplier_name: str
    orders: int
    receipts: int
    amount: Decimal
    short_rate: Decimal
    defect_rate: Decimal
    price_rate: Decimal
    on_time_rate: Decimal
    response_hours: Decimal | None
    score: Decimal | None = None  # qabul yo'q — baholanmaydi
    penalties: dict[str, Decimal] | None = None  # ko'rsatkich → ayirilgan ball (0.1 aniqlikda)


@dataclass(frozen=True, slots=True)
class ProductPrice:
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    amount: Decimal
    avg_price: Decimal
    prev_avg_price: Decimal | None
    best_price: Decimal | None  # hozirgi eng arzon faol taklif (bazaviy birlik)
    best_supplier: str | None
    overpay: Decimal  # (o'rtacha to'langan - eng arzon) x miqdor, > 0 bo'lsa
    change_pct: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PricePoint:
    day: date
    supplier_name: str
    price: Decimal  # bazaviy birlik uchun
    source: str  # offer (taklif tarixi) | receipt (qabul fakti)


@dataclass(frozen=True, slots=True)
class StockItem:
    store_id: UUID
    store_name: str
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    value: Decimal
    avg_daily: Decimal
    days_cover: Decimal | None  # sarf yo'q — None
    dead: bool  # qoldiq bor, oxirgi oynada sarf yo'q (neliquid)


@dataclass(frozen=True, slots=True)
class StockOverview:
    total_value: Decimal
    dead_value: Decimal
    items: tuple[StockItem, ...]


@dataclass(frozen=True, slots=True)
class ControlItem:
    kind: str  # price_change | discrepancy | role_conflict | manual_increase | payment_without_proof
    entity_id: UUID
    number: str
    title: str
    detail: str
    amount: Decimal | None
    at: date


class AnalyticsReader(Protocol):
    async def summary(self, *, stores: list[UUID] | None, period: Period, today: date) -> Summary: ...

    async def suppliers(self, *, stores: list[UUID] | None, period: Period) -> list[SupplierRating]: ...

    async def prices(self, *, stores: list[UUID] | None, period: Period, limit: int) -> list[ProductPrice]: ...

    async def price_history(self, product_id: UUID, *, since: date) -> list[PricePoint]: ...

    async def stock(self, *, stores: list[UUID] | None, today: date, window_days: int, limit: int) -> StockOverview: ...

    async def control(self, *, stores: list[UUID] | None, period: Period) -> list[ControlItem]: ...


def _scope(actor: Principal, roles: tuple[Role, ...], store_id: UUID | None) -> list[UUID] | None:
    """Ombor doirasi: rol omborsiz berilgan — hammasi (yoki so'ralgan ombor); aks holda faqat o'z omborlari."""
    actor.require(*roles, store_id=store_id)
    grants = [g for g in actor.grants if g.role in roles]
    if store_id is not None:
        return [store_id]
    if any(g.store_id is None for g in grants):
        return None
    return [g.store_id for g in grants if g.store_id]


class Reports:
    def __init__(self, reader: AnalyticsReader, *, window_days: int = 28, clock: Clock = utc_now) -> None:
        self._reader = reader
        self._window = window_days
        self._clock = clock

    def period(self, date_from: date | None, date_to: date | None) -> Period:
        """Default: oxirgi 30 kun (bugun ham kiradi)."""
        today = business_today(self._clock)
        end = date_to or today + timedelta(days=1)
        start = date_from or end - timedelta(days=DEFAULT_PERIOD_DAYS)
        if start >= end or (end - start).days > MAX_PERIOD_DAYS:
            raise InvalidReportError("analytics.period_range", max=MAX_PERIOD_DAYS)
        return Period(start, end)

    async def summary(self, actor: Principal, *, store_id: UUID | None = None) -> Summary:
        stores = _scope(actor, VIEWERS, store_id)
        today = business_today(self._clock)
        month = Period(today.replace(day=1), today + timedelta(days=1))  # oy boshidan bugungacha
        return await self._reader.summary(stores=stores, period=month, today=today)

    async def suppliers(
        self, actor: Principal, *, period: Period, store_id: UUID | None = None
    ) -> list[SupplierRating]:
        rows = await self._reader.suppliers(stores=_scope(actor, VIEWERS, store_id), period=period)
        rated = [_rated(r) if r.receipts else r for r in rows]
        return sorted(rated, key=lambda r: (r.score is None, -(r.score or 0), -r.amount))

    async def prices(self, actor: Principal, *, period: Period, store_id: UUID | None = None) -> list[ProductPrice]:
        rows = await self._reader.prices(stores=_scope(actor, VIEWERS, store_id), period=period, limit=200)
        return [replace(r, change_pct=change_pct(r.avg_price, r.prev_avg_price)) for r in rows]

    async def price_history(self, actor: Principal, product_id: UUID, *, days: int = 180) -> list[PricePoint]:
        actor.require(*VIEWERS)
        return await self._reader.price_history(product_id, since=business_today(self._clock) - timedelta(days=days))

    async def stock(self, actor: Principal, *, store_id: UUID | None = None) -> StockOverview:
        return await self._reader.stock(
            stores=_scope(actor, VIEWERS, store_id),
            today=business_today(self._clock),
            window_days=self._window,
            limit=200,
        )

    async def control(self, actor: Principal, *, period: Period, store_id: UUID | None = None) -> list[ControlItem]:
        items = await self._reader.control(stores=_scope(actor, CONTROLLERS, store_id), period=period)
        return sorted(items, key=lambda i: i.at, reverse=True)


def _rated(row: SupplierRating) -> SupplierRating:
    rates = {
        "short_rate": row.short_rate,
        "defect_rate": row.defect_rate,
        "price_rate": row.price_rate,
        "on_time_rate": row.on_time_rate,
    }
    penalties = {k: v.quantize(Decimal("0.1"), ROUND_HALF_UP) for k, v in score_penalties(**rates).items()}
    return replace(row, score=supplier_score(**rates), penalties=penalties)
