"""receiving port'lari → boshqa modullarning public interfeysi (procurement.OrderReceiving, catalog.CatalogQueries)."""

from collections.abc import Iterable
from uuid import UUID

from zakup.modules.catalog.application.queries import CatalogQueries
from zakup.modules.procurement.application.receiving_facade import OrderReceiving
from zakup.modules.receiving.application.ports import ExpectedOrder, ExpectedOrderLine


class OrdersAdapter:
    def __init__(self, orders: OrderReceiving) -> None:
        self._orders = orders

    async def expected(self, order_id: UUID) -> ExpectedOrder:
        order = await self._orders.expected(order_id)
        return ExpectedOrder(
            order_id=order.order_id,
            number=order.number,
            store_id=order.store_id,
            supplier_id=order.supplier_id,
            lines=tuple(
                ExpectedOrderLine(
                    order_line_id=line.order_line_id,
                    product_id=line.product_id,
                    product_name=line.product_name,
                    base_unit=line.base_unit,
                    qty=line.qty,
                    price=line.price,
                )
                for line in order.lines
            ),
        )

    async def mark_received(self, order_id: UUID, *, complete: bool) -> None:
        await self._orders.mark_received(order_id, complete=complete)


class LabelsAdapter:
    def __init__(self, catalog: CatalogQueries) -> None:
        self._catalog = catalog

    async def labels(
        self, *, products: Iterable[UUID] = (), suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> tuple[dict[UUID, str], dict[UUID, str], dict[UUID, str]]:
        labels = await self._catalog.labels(products=products, suppliers=suppliers, stores=stores)
        return {pid: name for pid, (name, _) in labels.products.items()}, labels.suppliers, labels.stores
