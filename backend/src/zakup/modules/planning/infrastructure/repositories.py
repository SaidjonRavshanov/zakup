from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.planning.application.facade import ConsumptionRow, StockRow
from zakup.modules.planning.infrastructure.tables import consumption_daily, stock_current

BATCH = 5000


class SqlPlanningStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_stock(self, store_ids: set[UUID], rows: list[StockRow], *, taken_at: datetime) -> None:
        if not store_ids:
            return
        await self._session.execute(delete(stock_current).where(stock_current.c.store_id.in_(store_ids)))
        await self._insert(
            stock_current,
            [
                {"store_id": r.store_id, "product_id": r.product_id, "qty": r.qty, "taken_at": taken_at}
                for r in rows
                if r.store_id in store_ids
            ],
        )

    async def replace_consumption(
        self, store_ids: set[UUID], rows: list[ConsumptionRow], *, date_from: date, date_to: date
    ) -> None:
        if not store_ids:
            return
        await self._session.execute(
            delete(consumption_daily).where(
                consumption_daily.c.store_id.in_(store_ids),
                consumption_daily.c.day >= date_from,
                consumption_daily.c.day < date_to,
            )
        )
        await self._insert(
            consumption_daily,
            [
                {"store_id": r.store_id, "product_id": r.product_id, "day": r.day, "qty": r.qty}
                for r in rows
                if r.store_id in store_ids and date_from <= r.day < date_to
            ],
        )

    async def consumption_totals(
        self, store_id: UUID, product_ids: Iterable[UUID], *, date_from: date, date_to: date
    ) -> dict[UUID, Decimal]:
        ids = list(product_ids)
        if not ids:
            return {}
        query = (
            select(consumption_daily.c.product_id, func.sum(consumption_daily.c.qty))
            .where(
                consumption_daily.c.store_id == store_id,
                consumption_daily.c.product_id.in_(ids),
                consumption_daily.c.day >= date_from,
                consumption_daily.c.day < date_to,
            )
            .group_by(consumption_daily.c.product_id)
        )
        return {row[0]: row[1] for row in (await self._session.execute(query)).all()}

    async def first_day(self, store_id: UUID) -> date | None:
        first: date | None = await self._session.scalar(
            select(func.min(consumption_daily.c.day)).where(consumption_daily.c.store_id == store_id)
        )
        return first

    async def stock(self, store_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, tuple[Decimal, datetime]]:
        ids = list(product_ids)
        if not ids:
            return {}
        query = select(stock_current).where(stock_current.c.store_id == store_id, stock_current.c.product_id.in_(ids))
        return {row.product_id: (row.qty, row.taken_at) for row in (await self._session.execute(query)).all()}

    async def has_history(self) -> bool:
        return bool(await self._session.scalar(select(select(consumption_daily).exists())))

    async def _insert(self, table: object, rows: list[dict[str, object]]) -> None:
        for start in range(0, len(rows), BATCH):
            await self._session.execute(insert(table), rows[start : start + BATCH])  # type: ignore[arg-type]
