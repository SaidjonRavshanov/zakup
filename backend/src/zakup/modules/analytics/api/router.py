"""Tahlil va nazorat HTTP API (faqat o'qish)."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from zakup.modules.analytics.application.reports import Period, Reports
from zakup.platform.di import Stub
from zakup.platform.security import CurrentPrincipal

router = APIRouter(prefix="/analytics", tags=["analytics"])

ReportsDep = Annotated[Reports, Depends(Stub(Reports))]
StoreQuery = Annotated[UUID | None, Query()]
DateQuery = Annotated[date | None, Query()]


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PeriodOut(Model):
    date_from: date
    date_to: date


class SummaryOut(Model):
    period: PeriodOut
    purchases: Decimal
    purchases_prev: Decimal
    receipts: int
    savings: Decimal
    overpay: Decimal
    defect_loss: Decimal
    price_change_pct: Decimal | None
    pending_requests: int
    auto_drafts: int
    orders_in_transit: int
    arriving_today: int
    open_disputes: int
    debt: Decimal
    overdue: Decimal


class SupplierRatingOut(Model):
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
    score: Decimal | None
    penalties: dict[str, Decimal] | None  # short / defect / price / late → ayirilgan ball


class ProductPriceOut(Model):
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    amount: Decimal
    avg_price: Decimal
    prev_avg_price: Decimal | None
    change_pct: Decimal | None
    best_price: Decimal | None
    best_supplier: str | None
    overpay: Decimal


class PricePointOut(Model):
    day: date
    supplier_name: str
    price: Decimal
    source: str


class StockItemOut(Model):
    store_id: UUID
    store_name: str
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    value: Decimal
    avg_daily: Decimal
    days_cover: Decimal | None
    dead: bool


class StockOut(Model):
    total_value: Decimal
    dead_value: Decimal
    items: list[StockItemOut]


class ControlItemOut(Model):
    kind: str
    entity_id: UUID
    number: str
    title: str
    detail: str
    amount: Decimal | None
    at: date


class Report[T](BaseModel):
    period: PeriodOut
    items: list[T]


def _period(reports: Reports, date_from: date | None, date_to: date | None) -> Period:
    return reports.period(date_from, date_to)


def _period_out(period: Period) -> PeriodOut:
    return PeriodOut(date_from=period.date_from, date_to=period.date_to)


@router.get("/summary")
async def summary(actor: CurrentPrincipal, reports: ReportsDep, store_id: StoreQuery = None) -> SummaryOut:
    return SummaryOut.model_validate(await reports.summary(actor, store_id=store_id))


@router.get("/suppliers")
async def suppliers(
    actor: CurrentPrincipal,
    reports: ReportsDep,
    store_id: StoreQuery = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> Report[SupplierRatingOut]:
    period = _period(reports, date_from, date_to)
    items = await reports.suppliers(actor, period=period, store_id=store_id)
    return Report[SupplierRatingOut](
        period=_period_out(period), items=[SupplierRatingOut.model_validate(i) for i in items]
    )


@router.get("/prices")
async def prices(
    actor: CurrentPrincipal,
    reports: ReportsDep,
    store_id: StoreQuery = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> Report[ProductPriceOut]:
    period = _period(reports, date_from, date_to)
    items = await reports.prices(actor, period=period, store_id=store_id)
    return Report[ProductPriceOut](period=_period_out(period), items=[ProductPriceOut.model_validate(i) for i in items])


@router.get("/prices/{product_id}")
async def price_history(
    product_id: UUID, actor: CurrentPrincipal, reports: ReportsDep, days: Annotated[int, Query(ge=7, le=730)] = 180
) -> list[PricePointOut]:
    return [PricePointOut.model_validate(p) for p in await reports.price_history(actor, product_id, days=days)]


@router.get("/stock")
async def stock(actor: CurrentPrincipal, reports: ReportsDep, store_id: StoreQuery = None) -> StockOut:
    return StockOut.model_validate(await reports.stock(actor, store_id=store_id))


@router.get("/control")
async def control(
    actor: CurrentPrincipal,
    reports: ReportsDep,
    store_id: StoreQuery = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> Report[ControlItemOut]:
    period = _period(reports, date_from, date_to)
    items = await reports.control(actor, period=period, store_id=store_id)
    return Report[ControlItemOut](period=_period_out(period), items=[ControlItemOut.model_validate(i) for i in items])


__all__: list[Any] = ["router"]
