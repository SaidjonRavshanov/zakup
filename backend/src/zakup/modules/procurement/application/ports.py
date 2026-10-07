"""procurement port'lari (DIP). catalog bilan — faqat CatalogPort orqali (ARCHITECTURE §3.1)."""

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from zakup.modules.procurement.application.dto import (
    AutoCardInfo,
    CatalogLabels,
    DemandSnapshot,
    OfferInfo,
    OrderDetail,
    OrderListItem,
    RequestDetail,
    RequestListItem,
    SupplierInfo,
)
from zakup.modules.procurement.domain.order import OrderStatus, PurchaseOrder
from zakup.modules.procurement.domain.request import PurchaseRequest, RequestStatus


class RequestRepository(Protocol):
    async def next_number(self) -> str: ...

    async def open_products(self, store_id: UUID) -> set[UUID]:
        """Ochiq (qoralama / tasdiqlashda) zayavkalardagi tovarlar — avto-zayavka ularni takrorlamaydi."""

    async def has_auto_on(self, store_id: UUID, day: date) -> bool:
        """Shu kuni ombor uchun avto-zayavka yaratilganmi (Toshkent sanasi)."""

    async def get(self, request_id: UUID) -> PurchaseRequest | None: ...

    async def add(self, request: PurchaseRequest) -> None: ...

    async def save(self, request: PurchaseRequest) -> None:
        """Optimistic lock; yangi tasdiqlash yozuvlari (pull_new_approvals) ham saqlanadi."""


class OrderRepository(Protocol):
    async def next_number(self) -> str: ...

    async def in_transit(
        self, store_id: UUID, product_ids: Iterable[UUID], received_after: datetime | None = None
    ) -> dict[UUID, Decimal]:
        """Yo'lda: yuborilgan / tasdiqlangan, hali qabul qilinmagan buyurtmalar (bazaviy birlikda).

        `received_after` — qoldiq snapshot vaqti: undan keyin qabul qilinganlar ham "yo'lda" (iiko qoldig'ida
        hali yo'q — aks holda ertalabki avto-zayavka kelgan tovarni yana buyuradi)."""

    async def get(self, order_id: UUID) -> PurchaseOrder | None: ...

    async def add(self, order: PurchaseOrder) -> None: ...

    async def save(self, order: PurchaseOrder) -> None: ...


class ResponseTokens(Protocol):
    """Yetkazuvchi uchun ro'yxatsiz havola (WORKFLOW B7): xom token faqat bir marta qaytariladi, bazada — hash."""

    async def issue(self, order_id: UUID, *, expires_at: datetime) -> str: ...

    async def resolve(self, raw_token: str, *, now: datetime) -> UUID | None: ...


class CatalogPort(Protocol):
    async def offer(self, offer_id: UUID) -> OfferInfo | None: ...

    async def default_offer(self, product_id: UUID, store_id: UUID) -> OfferInfo | None: ...

    async def pack_quantity(self, offer_id: UUID, base_qty: Decimal) -> Decimal | None:
        """Bazaviy miqdor → yetkazuvchi qadoqlari (karralilikkacha yuqoriga)."""

    async def product_available(self, product_id: UUID) -> bool: ...

    async def store_available(self, store_id: UUID) -> bool: ...

    async def supplier(self, supplier_id: UUID) -> SupplierInfo | None: ...

    async def auto_cards(self, store_id: UUID | None) -> list[AutoCardInfo]: ...

    async def labels(
        self, *, products: Iterable[UUID] = (), suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> CatalogLabels: ...


class DemandPort(Protocol):
    """planning modulining public interfeysi (DemandQueries) — adapter orqali."""

    async def stats(
        self, store_id: UUID, product_ids: Iterable[UUID], *, today: date
    ) -> dict[UUID, DemandSnapshot]: ...


class SupplierCreditPort(Protocol):
    """Yetkazuvchi qarzi (finance facade'i, bootstrap ulaydi): `overdue` / `over_limit` yoki None (WORKFLOW B12)."""

    async def check(self, supplier_id: UUID, amount: Decimal) -> str | None: ...


class RequestReader(Protocol):
    async def list(
        self, *, statuses: set[RequestStatus] | None, store_ids: set[UUID] | None, initiator_id: UUID | None, limit: int
    ) -> list[RequestListItem]: ...

    async def detail(self, request_id: UUID) -> RequestDetail | None: ...


class OrderReader(Protocol):
    async def list(
        self, *, statuses: set[OrderStatus] | None, store_ids: set[UUID] | None, request_id: UUID | None, limit: int
    ) -> list[OrderListItem]: ...

    async def detail(self, order_id: UUID) -> OrderDetail | None: ...
