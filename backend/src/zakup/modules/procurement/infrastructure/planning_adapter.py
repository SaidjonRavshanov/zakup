"""procurement DemandPort → planning public interfeysi (DemandQueries)."""

from collections.abc import Iterable
from datetime import date
from uuid import UUID

from zakup.modules.planning.application.facade import DemandQueries
from zakup.modules.procurement.application.dto import DemandSnapshot


class DemandAdapter:
    def __init__(self, queries: DemandQueries) -> None:
        self._queries = queries

    async def stats(self, store_id: UUID, product_ids: Iterable[UUID], *, today: date) -> dict[UUID, DemandSnapshot]:
        stats = await self._queries.stats(store_id, product_ids, today=today)
        return {
            product_id: DemandSnapshot(
                avg_daily=s.avg_daily,
                days_observed=s.days_observed,
                window_days=s.window_days,
                stock=s.stock,
                stock_at=s.stock_at,
            )
            for product_id, s in stats.items()
        }
