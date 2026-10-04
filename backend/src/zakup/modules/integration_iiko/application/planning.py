"""iiko → planning: omborlardagi qoldiq va kunlik sarf (avto-zakup uchun, WORKFLOW B3).

Omborlar va tovarlar bog'lanishi (iiko.links) shu serverning ma'lumotnoma sinxronidan keladi;
bog'lanmagan ombor / tovar (masalan, taom, xizmat) — tashlab yuboriladi.
"""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from zakup.modules.integration_iiko.application.ports import (
    ConsumptionLine,
    EntityKind,
    IikoReader,
    Links,
    PlanningSync,
    StockLine,
)
from zakup.modules.integration_iiko.application.sync import Stats

# Sarf deb hisoblanadigan chiqimlar (Sebzar OLAP namunasi, 2026-10-03): sotuv bo'yicha retsept, hisobdan chiqarish,
# ishlab chiqarishga, boshqa omborga ko'chirish (asosiy ombor oshxonalarni ta'minlaydi), chiqim nakladnoy.
# Inventarizatsiya tuzatishi — anomaliya, hisobga olinmaydi.
CONSUMPTION_TYPES = frozenset(
    {"SESSION_WRITEOFF", "WRITEOFF", "PRODUCTION", "DISASSEMBLE", "TRANSFER", "OUTGOING_INVOICE"}
)


class ImportStock:
    def __init__(self, links: Links, planning: PlanningSync) -> None:
        self._links = links
        self._planning = planning

    async def __call__(self, server: str, reader: IikoReader, at: datetime) -> dict[str, int]:
        stats = Stats()
        stores = await self._links.mapping(server, EntityKind.STORE)
        products = await self._links.mapping(server, EntityKind.PRODUCT)
        rows = []
        for balance in await reader.stock_balances(at):
            store_id, product_id = stores.get(balance.store_id), products.get(balance.product_id)
            if store_id is None or product_id is None:
                stats.add("balances_skipped")
                continue
            rows.append(StockLine(store_id, product_id, balance.amount))
            stats.add("balances")
        await self._planning.replace_stock(set(stores.values()), rows, taken_at=at)
        return stats.as_dict()


class ImportConsumption:
    def __init__(self, links: Links, planning: PlanningSync) -> None:
        self._links = links
        self._planning = planning

    async def __call__(self, server: str, reader: IikoReader, date_from: date, date_to: date) -> dict[str, int]:
        stats = Stats()
        stores = await self._links.mapping(server, EntityKind.STORE)
        products = await self._links.mapping(server, EntityKind.PRODUCT)
        daily: dict[tuple[UUID, UUID, date], Decimal] = defaultdict(Decimal)
        for movement in await reader.movements(date_from, date_to):
            if movement.type not in CONSUMPTION_TYPES:
                continue
            store_id, product_id = stores.get(movement.store_id), products.get(movement.product_id)
            if store_id is None or product_id is None:
                stats.add("movements_skipped")
                continue
            daily[(store_id, product_id, movement.day)] += movement.amount_out
            stats.add("movements")
        rows = [ConsumptionLine(s, p, day, qty) for (s, p, day), qty in daily.items()]
        stats.add("days_products", len(rows))
        await self._planning.replace_consumption(set(stores.values()), rows, date_from=date_from, date_to=date_to)
        return stats.as_dict()
