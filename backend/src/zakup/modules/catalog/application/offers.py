"""Yetkazib beruvchi takliflari (tovar ↔ yetkazib beruvchi tovari) va narx tarixi."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.application.common import load
from zakup.modules.catalog.application.dto import OfferCommand, PriceHistoryItem
from zakup.modules.catalog.application.ports import (
    OfferRepository,
    PriceHistory,
    PriceHistoryReader,
    ProductRepository,
    SupplierRepository,
)
from zakup.modules.catalog.domain.offer import (
    DuplicateOfferError,
    InvalidOfferError,
    Packaging,
    PriceSource,
    SupplierOffer,
)
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, business_today, utc_now
from zakup.shared_kernel.uow import UnitOfWork

EDITORS = (Role.BUYER, Role.ADMIN)


def _packaging(cmd: OfferCommand) -> Packaging:
    return Packaging(unit=cmd.pack_unit, factor=cmd.pack_factor, multiple=cmd.order_multiple)


class AddOffer:
    def __init__(
        self,
        uow: UnitOfWork,
        offers: OfferRepository,
        history: PriceHistory,
        suppliers: SupplierRepository,
        products: ProductRepository,
        *,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._offers = offers
        self._history = history
        self._suppliers = suppliers
        self._products = products
        self._clock = clock

    async def __call__(
        self, actor: Principal, supplier_id: UUID, product_id: UUID, cmd: OfferCommand, price: Decimal
    ) -> UUID:
        actor.require(*EDITORS)
        async with self._uow:
            supplier = await load(self._suppliers, supplier_id, "supplier.not_found")
            product = await load(self._products, product_id, "product.not_found")
            if supplier.is_archived or product.is_archived:
                raise InvalidOfferError("offer.archived_party")
            sku = (cmd.supplier_sku or "").strip() or None
            if await self._offers.exists(supplier_id=supplier.id, product_id=product.id, supplier_sku=sku):
                raise DuplicateOfferError("offer.duplicate")
            offer, record = SupplierOffer.create(
                supplier_id=supplier.id,
                product_id=product.id,
                packaging=_packaging(cmd),
                price=price,
                valid_from=business_today(self._clock),
                supplier_sku=sku,
                supplier_name=cmd.supplier_product_name,
            )
            await self._offers.add(offer)
            await self._history.append(record)
            await self._uow.commit()
            return offer.id


class ReviseOffer:
    """Qadoq / artikul tahriri va (o'zgargan bo'lsa) narx — narx tarixiga yoziladi."""

    def __init__(self, uow: UnitOfWork, offers: OfferRepository, history: PriceHistory, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._offers = offers
        self._history = history
        self._clock = clock

    async def __call__(
        self,
        actor: Principal,
        offer_id: UUID,
        cmd: OfferCommand,
        price: Decimal,
        valid_from: date | None = None,
    ) -> None:
        actor.require(*EDITORS)
        async with self._uow:
            offer = await load(self._offers, offer_id, "offer.not_found")
            offer.revise(
                supplier_sku=cmd.supplier_sku, supplier_name=cmd.supplier_product_name, packaging=_packaging(cmd)
            )
            record = offer.change_price(price, valid_from or business_today(self._clock), PriceSource.MANUAL)
            await self._offers.save(offer)
            if record is not None:
                await self._history.append(record)
            self._uow.track(offer)
            await self._uow.commit()


class ArchiveOffer:
    def __init__(self, uow: UnitOfWork, offers: OfferRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._offers = offers
        self._clock = clock

    async def __call__(self, actor: Principal, offer_id: UUID) -> None:
        actor.require(*EDITORS)
        async with self._uow:
            offer = await load(self._offers, offer_id, "offer.not_found")
            offer.archive(self._clock())
            await self._offers.save(offer)
            await self._uow.commit()


class GetPriceHistory:
    def __init__(self, reader: PriceHistoryReader) -> None:
        self._reader = reader

    async def __call__(self, offer_id: UUID, *, limit: int = 50) -> list[PriceHistoryItem]:
        return await self._reader.history(offer_id, limit=max(1, min(limit, 500)))
