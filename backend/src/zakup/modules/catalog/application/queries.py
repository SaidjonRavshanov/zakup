"""catalog modulining boshqa modullar (procurement va h.k.) uchun public o'qish interfeysi (ARCHITECTURE §3.1).

Natija — oddiy DTO'lar; chaqiruvchi catalog jadvallari va aggregate'larini bilmaydi.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.application.dto import Labels
from zakup.modules.catalog.application.ports import (
    LabelReader,
    OfferRepository,
    OffersByProduct,
    ProductRepository,
    PurchaseCardRepository,
    StoreRepository,
    SupplierRepository,
)
from zakup.modules.catalog.domain.offer import SupplierOffer


@dataclass(frozen=True, slots=True)
class OfferQuote:
    offer_id: UUID
    supplier_id: UUID
    product_id: UUID
    pack_unit: str
    pack_factor: Decimal
    order_multiple: Decimal
    price_per_pack: Decimal
    price_per_base: Decimal
    supplier_sku: str | None
    available: bool  # taklif ham, yetkazuvchi ham arxivda emas


@dataclass(frozen=True, slots=True)
class PackQuantity:
    packs: Decimal
    base_qty: Decimal


@dataclass(frozen=True, slots=True)
class SupplierTerms:
    supplier_id: UUID
    name: str
    min_order_amount: Decimal
    lead_time_days: int
    phone: str | None
    telegram: str | None


class CatalogQueries:
    def __init__(
        self,
        *,
        offers: OfferRepository,
        products: ProductRepository,
        suppliers: SupplierRepository,
        stores: StoreRepository,
        cards: PurchaseCardRepository,
        offers_by_product: OffersByProduct,
        labels: LabelReader,
    ) -> None:
        self._offers = offers
        self._products = products
        self._suppliers = suppliers
        self._stores = stores
        self._cards = cards
        self._offers_by_product = offers_by_product
        self._labels = labels

    async def offer(self, offer_id: UUID) -> OfferQuote | None:
        offer = await self._offers.get(offer_id)
        return await self._quote(offer) if offer else None

    async def default_offer(self, product_id: UUID, store_id: UUID) -> OfferQuote | None:
        """Tanlov tartibi (WORKFLOW B6): kartochkadagi asosiy → muqobil → bazaviy birligi eng arzon faol taklif."""
        offers = [
            q for q in [await self._quote(o) for o in await self._offers_by_product.active(product_id)] if q.available
        ]
        if not offers:
            return None
        card = await self._cards.find(product_id=product_id, store_id=store_id)
        if card is not None:
            for supplier_id in (card.suppliers.primary_id, card.suppliers.alternative_id):
                preferred = [q for q in offers if q.supplier_id == supplier_id]
                if preferred:
                    return min(preferred, key=lambda q: q.price_per_base)
        return min(offers, key=lambda q: q.price_per_base)

    async def pack_quantity(self, offer_id: UUID, base_qty: Decimal) -> PackQuantity | None:
        offer = await self._offers.get(offer_id)
        if offer is None:
            return None
        quantity = offer.order_quantity(base_qty)
        return PackQuantity(packs=quantity.packs, base_qty=quantity.base_qty)

    async def product_available(self, product_id: UUID) -> bool:
        product = await self._products.get(product_id)
        return product is not None and not product.is_archived

    async def store_available(self, store_id: UUID) -> bool:
        store = await self._stores.get(store_id)
        return store is not None and not store.is_archived

    async def supplier_terms(self, supplier_id: UUID) -> SupplierTerms | None:
        supplier = await self._suppliers.get(supplier_id)
        if supplier is None:
            return None
        return SupplierTerms(
            supplier_id=supplier.id,
            name=supplier.name,
            min_order_amount=supplier.min_order_amount.amount,
            lead_time_days=supplier.schedule.lead_time_days,
            phone=supplier.contacts.phone,
            telegram=supplier.contacts.telegram,
        )

    async def labels(
        self, *, products: Iterable[UUID] = (), suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> Labels:
        return await self._labels.labels(products=set(products), suppliers=set(suppliers), stores=set(stores))

    async def _quote(self, offer: SupplierOffer) -> OfferQuote:
        supplier = await self._suppliers.get(offer.supplier_id)
        return OfferQuote(
            offer_id=offer.id,
            supplier_id=offer.supplier_id,
            product_id=offer.product_id,
            pack_unit=offer.packaging.unit.value,
            pack_factor=offer.packaging.factor,
            order_multiple=offer.packaging.multiple,
            price_per_pack=offer.price,
            price_per_base=offer.base_unit_price,
            supplier_sku=offer.supplier_sku,
            available=not offer.is_archived and supplier is not None and not supplier.is_archived,
        )
