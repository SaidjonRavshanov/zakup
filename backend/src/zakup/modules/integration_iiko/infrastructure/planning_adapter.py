"""integration_iiko PlanningSync → planning public interfeysi (PlanningIngest)."""

from datetime import date, datetime
from uuid import UUID

from zakup.modules.integration_iiko.application.ports import ConsumptionLine, StockLine
from zakup.modules.planning.application.facade import ConsumptionRow, PlanningIngest, StockRow


class PlanningAdapter:
    def __init__(self, ingest: PlanningIngest) -> None:
        self._ingest = ingest

    async def replace_stock(self, store_ids: set[UUID], rows: list[StockLine], *, taken_at: datetime) -> None:
        await self._ingest.replace_stock(
            store_ids, [StockRow(r.store_id, r.product_id, r.qty) for r in rows], taken_at=taken_at
        )

    async def replace_consumption(
        self, store_ids: set[UUID], rows: list[ConsumptionLine], *, date_from: date, date_to: date
    ) -> None:
        await self._ingest.replace_consumption(
            store_ids,
            [ConsumptionRow(r.store_id, r.product_id, r.day, r.qty) for r in rows],
            date_from=date_from,
            date_to=date_to,
        )
