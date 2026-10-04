"""CatalogPort → catalog modulining public interfeysi (CatalogQueries)."""

from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.application.queries import CatalogQueries, OfferQuote
from zakup.modules.procurement.application.dto import CatalogLabels, OfferInfo, SupplierInfo


def _offer(quote: OfferQuote) -> OfferInfo:
    return OfferInfo(
        offer_id=quote.offer_id,
        supplier_id=quote.supplier_id,
        product_id=quote.product_id,
        pack_unit=quote.pack_unit,
        pack_factor=quote.pack_factor,
        price_per_pack=quote.price_per_pack,
        price_per_base=quote.price_per_base,
        supplier_sku=quote.supplier_sku,
        available=quote.available,
    )


class CatalogAdapter:
    def __init__(self, catalog: CatalogQueries) -> None:
        self._catalog = catalog

    async def offer(self, offer_id: UUID) -> OfferInfo | None:
        quote = await self._catalog.offer(offer_id)
        return _offer(quote) if quote else None

    async def default_offer(self, product_id: UUID, store_id: UUID) -> OfferInfo | None:
        quote = await self._catalog.default_offer(product_id, store_id)
        return _offer(quote) if quote else None

    async def pack_quantity(self, offer_id: UUID, base_qty: Decimal) -> Decimal | None:
        quantity = await self._catalog.pack_quantity(offer_id, base_qty)
        return quantity.packs if quantity else None

    async def product_available(self, product_id: UUID) -> bool:
        return await self._catalog.product_available(product_id)

    async def store_available(self, store_id: UUID) -> bool:
        return await self._catalog.store_available(store_id)

    async def supplier(self, supplier_id: UUID) -> SupplierInfo | None:
        terms = await self._catalog.supplier_terms(supplier_id)
        if terms is None:
            return None
        return SupplierInfo(
            supplier_id=terms.supplier_id,
            name=terms.name,
            min_order_amount=terms.min_order_amount,
            lead_time_days=terms.lead_time_days,
            phone=terms.phone,
            telegram=terms.telegram,
        )

    async def labels(
        self, *, products: Iterable[UUID] = (), suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> CatalogLabels:
        labels = await self._catalog.labels(products=products, suppliers=suppliers, stores=stores)
        return CatalogLabels(
            products={pid: (name, unit.value) for pid, (name, unit) in labels.products.items()},
            suppliers=labels.suppliers,
            stores=labels.stores,
        )
