"""Buyurtma (PO) use case'lari: yuborish, yetkazuvchi javobi, qayta tasdiqlash, bekor qilish (WORKFLOW B6, B7)."""

from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from zakup.modules.procurement.application.dto import OrderDetail, OrderListItem, SentOrder
from zakup.modules.procurement.application.message import order_message
from zakup.modules.procurement.application.ports import CatalogPort, OrderReader, OrderRepository, ResponseTokens
from zakup.modules.procurement.application.requests import DECIDERS, MANAGERS, OVERSEERS, scoped_stores
from zakup.modules.procurement.domain.approval import ApprovalPolicy
from zakup.modules.procurement.domain.order import Channel, LineResponse, OrderStatus, PurchaseOrder, Tolerance
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.errors import NotFoundError, UnauthenticatedError
from zakup.shared_kernel.uow import UnitOfWork

TOKEN_TTL = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class OrderSettings:
    tolerance: Tolerance
    response_hours: int
    public_base_url: str  # yetkazuvchi havolasi: {base}/s/{token}
    company_name: str


async def _load(orders: OrderRepository, order_id: UUID) -> PurchaseOrder:
    order = await orders.get(order_id)
    if order is None:
        raise NotFoundError("order.not_found")
    return order


async def _enrich(detail: OrderDetail, catalog: CatalogPort) -> OrderDetail:
    labels = await catalog.labels(
        products={line.product_id for line in detail.lines}, suppliers={detail.supplier_id}, stores={detail.store_id}
    )
    supplier = await catalog.supplier(detail.supplier_id)
    warnings = []
    if supplier and supplier.min_order_amount and detail.total < supplier.min_order_amount:
        warnings.append("below_min_order")
    return replace(
        detail,
        lines=tuple(
            replace(line, product_name=labels.product(line.product_id)[0], base_unit=labels.product(line.product_id)[1])
            for line in detail.lines
        ),
        supplier_name=labels.suppliers.get(detail.supplier_id),
        supplier_phone=supplier.phone if supplier else None,
        supplier_telegram=supplier.telegram if supplier else None,
        min_order_amount=supplier.min_order_amount if supplier else Decimal(0),
        store_name=labels.stores.get(detail.store_id),
        warnings=tuple(warnings),
    )


class ListOrders:
    def __init__(self, reader: OrderReader, catalog: CatalogPort) -> None:
        self._reader = reader
        self._catalog = catalog

    async def __call__(
        self, actor: Principal, *, statuses: set[OrderStatus] | None = None, limit: int = 100
    ) -> list[OrderListItem]:
        actor.require(*OVERSEERS, Role.STOREKEEPER)
        items = await self._reader.list(
            statuses=statuses,
            store_ids=scoped_stores(actor, (*OVERSEERS, Role.STOREKEEPER)),
            request_id=None,
            limit=max(1, min(limit, 200)),
        )
        labels = await self._catalog.labels(
            suppliers={item.supplier_id for item in items}, stores={item.store_id for item in items}
        )
        return [
            replace(
                item, supplier_name=labels.suppliers.get(item.supplier_id), store_name=labels.stores.get(item.store_id)
            )
            for item in items
        ]


class GetOrder:
    def __init__(self, reader: OrderReader, catalog: CatalogPort) -> None:
        self._reader = reader
        self._catalog = catalog

    async def __call__(self, actor: Principal, order_id: UUID) -> OrderDetail:
        detail = await self._reader.detail(order_id)
        if detail is None:
            raise NotFoundError("order.not_found")
        actor.require(*OVERSEERS, Role.STOREKEEPER, store_id=detail.store_id)
        return await _enrich(detail, self._catalog)


class SendOrder:
    """Yetkazuvchiga yuborish: matn + ro'yxatsiz javob havolasi. Matnni zakupshik Telegram/WhatsApp'da ulashadi."""

    def __init__(
        self,
        uow: UnitOfWork,
        orders: OrderRepository,
        reader: OrderReader,
        tokens: ResponseTokens,
        catalog: CatalogPort,
        *,
        settings: OrderSettings,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._orders = orders
        self._reader = reader
        self._tokens = tokens
        self._catalog = catalog
        self._settings = settings
        self._clock = clock

    async def __call__(self, actor: Principal, order_id: UUID, *, channel: Channel) -> SentOrder:
        async with self._uow:
            order = await _load(self._orders, order_id)
            actor.require(*MANAGERS, store_id=order.store_id)
            now = self._clock()
            order.send(
                by=actor.user_id, channel=channel, at=now, deadline=now + timedelta(hours=self._settings.response_hours)
            )
            await self._orders.save(order)
            token = await self._tokens.issue(order.id, expires_at=now + TOKEN_TTL)
            self._uow.track(order)
            detail = await self._reader.detail(order.id)
            assert detail is not None
            url = f"{self._settings.public_base_url.rstrip('/')}/s/{token}"
            message = order_message(await _enrich(detail, self._catalog), url=url, company=self._settings.company_name)
            await self._uow.commit()
            return SentOrder(message=message, response_url=url)


class RecordOrderResponse:
    """Zakupshik yetkazuvchi javobini qo'lda kiritadi (telefon / xabar orqali kelgan)."""

    def __init__(
        self, uow: UnitOfWork, orders: OrderRepository, settings: OrderSettings, clock: Clock = utc_now
    ) -> None:
        self._uow = uow
        self._orders = orders
        self._settings = settings
        self._clock = clock

    async def __call__(self, actor: Principal, order_id: UUID, responses: dict[UUID, LineResponse]) -> OrderStatus:
        async with self._uow:
            order = await _load(self._orders, order_id)
            actor.require(*MANAGERS, store_id=order.store_id)
            order.record_response(responses, self._settings.tolerance, at=self._clock())
            await self._orders.save(order)
            self._uow.track(order)
            await self._uow.commit()
            return order.status


class ApproveOrderChanges:
    """Dopuskdan tashqari narx: tasdiqlash matritsasi bo'yicha (summa — tasdiqlangan jami)."""

    def __init__(self, uow: UnitOfWork, orders: OrderRepository, policy: ApprovalPolicy) -> None:
        self._uow = uow
        self._orders = orders
        self._policy = policy

    async def __call__(self, actor: Principal, order_id: UUID) -> OrderStatus:
        async with self._uow:
            order = await _load(self._orders, order_id)
            actor.require(*DECIDERS, store_id=order.store_id)
            self._policy.ensure_can_approve(actor, order.store_id, order.confirmed_total)
            order.approve_changes()
            await self._orders.save(order)
            self._uow.track(order)
            await self._uow.commit()
            return order.status


class CancelOrder:
    def __init__(self, uow: UnitOfWork, orders: OrderRepository) -> None:
        self._uow = uow
        self._orders = orders

    async def __call__(self, actor: Principal, order_id: UUID, *, reason: str) -> None:
        async with self._uow:
            order = await _load(self._orders, order_id)
            actor.require(*DECIDERS, store_id=order.store_id)
            order.cancel(reason=reason)
            await self._orders.save(order)
            await self._uow.commit()


# ---------------------------------------------------------------- yetkazuvchi havolasi (ro'yxatsiz)


class GetPublicOrder:
    def __init__(
        self, tokens: ResponseTokens, reader: OrderReader, catalog: CatalogPort, clock: Clock = utc_now
    ) -> None:
        self._tokens = tokens
        self._reader = reader
        self._catalog = catalog
        self._clock = clock

    async def __call__(self, raw_token: str) -> OrderDetail:
        order_id = await self._tokens.resolve(raw_token, now=self._clock())
        detail = await self._reader.detail(order_id) if order_id else None
        if detail is None:
            raise UnauthenticatedError("order.link_invalid")
        enriched = await _enrich(detail, self._catalog)
        # Yetkazuvchiga ichki ma'lumot ko'rsatilmaydi
        return replace(enriched, supplier_phone=None, supplier_telegram=None, warnings=())


class SupplierRespond:
    def __init__(
        self,
        uow: UnitOfWork,
        orders: OrderRepository,
        tokens: ResponseTokens,
        settings: OrderSettings,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._orders = orders
        self._tokens = tokens
        self._settings = settings
        self._clock = clock

    async def __call__(self, raw_token: str, responses: dict[UUID, LineResponse]) -> OrderStatus:
        async with self._uow:
            now = self._clock()
            order_id = await self._tokens.resolve(raw_token, now=now)
            if order_id is None:
                raise UnauthenticatedError("order.link_invalid")
            order = await _load(self._orders, order_id)
            order.record_response(responses, self._settings.tolerance, at=now)
            await self._orders.save(order)
            self._uow.track(order)
            await self._uow.commit()
            return order.status
