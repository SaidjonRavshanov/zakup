"""procurement modulining receiving uchun public interfeysi (ARCHITECTURE §3.1: receiving → procurement)."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from zakup.modules.procurement.application.ports import CatalogPort, OrderRepository
from zakup.modules.procurement.domain.order import RECEIVABLE, OrderStatus
from zakup.shared_kernel.errors import InvalidTransitionError, NotFoundError


@dataclass(frozen=True, slots=True)
class LineToReceive:
    order_line_id: UUID
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal  # bazaviy birlikda
    price: Decimal  # bazaviy birlik uchun


@dataclass(frozen=True, slots=True)
class OrderToReceive:
    order_id: UUID
    number: str
    store_id: UUID
    supplier_id: UUID
    status: OrderStatus
    lines: tuple[LineToReceive, ...]


class OrderReceiving:
    def __init__(self, orders: OrderRepository, catalog: CatalogPort) -> None:
        self._orders = orders
        self._catalog = catalog

    async def expected(self, order_id: UUID) -> OrderToReceive:
        order = await self._orders.get(order_id)
        if order is None:
            raise NotFoundError("order.not_found")
        if order.status not in RECEIVABLE:
            raise InvalidTransitionError("order.not_receivable", status=order.status.value)
        expected = order.expected_lines
        labels = await self._catalog.labels(products={line.product_id for line, _, _ in expected})
        return OrderToReceive(
            order_id=order.id,
            number=order.number,
            store_id=order.store_id,
            supplier_id=order.supplier_id,
            status=order.status,
            lines=tuple(
                LineToReceive(
                    order_line_id=line.id,
                    product_id=line.product_id,
                    product_name=labels.product(line.product_id)[0],
                    base_unit=labels.product(line.product_id)[1],
                    qty=qty,
                    price=price,
                )
                for line, qty, price in expected
            ),
        )

    async def mark_received(self, order_id: UUID, *, complete: bool) -> None:
        order = await self._orders.get(order_id)
        if order is None:
            raise NotFoundError("order.not_found")
        order.mark_received(complete=complete)
        await self._orders.save(order)
