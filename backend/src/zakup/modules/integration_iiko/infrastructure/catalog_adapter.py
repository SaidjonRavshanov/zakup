"""CatalogSync port'i → catalog modulining public interfeysi (IikoCatalogSync)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.application.iiko_sync import IikoCatalogSync
from zakup.modules.integration_iiko.domain.mapping import PaymentMethod


class CatalogSyncAdapter:
    def __init__(self, catalog: IikoCatalogSync) -> None:
        self._catalog = catalog

    async def upsert_branch(self, local_id: UUID | None, *, iiko_id: UUID, code: str | None, name: str) -> UUID:
        return await self._catalog.upsert_branch(local_id, iiko_id=iiko_id, code=code, name=name)

    async def upsert_store(self, local_id: UUID | None, *, iiko_id: UUID, name: str, branch_id: UUID | None) -> UUID:
        return await self._catalog.upsert_store(local_id, iiko_id=iiko_id, name=name, branch_id=branch_id)

    async def upsert_category(self, local_id: UUID | None, *, iiko_id: UUID, name: str, parent_id: UUID | None) -> UUID:
        return await self._catalog.upsert_category(local_id, iiko_id=iiko_id, name=name, parent_id=parent_id)

    async def find_product_by_article(self, article: str) -> UUID | None:
        return await self._catalog.find_product_by_article(article)

    async def upsert_product(
        self,
        local_id: UUID | None,
        *,
        iiko_id: UUID,
        name: str,
        article: str | None,
        base_unit: str,
        category_id: UUID | None,
        archived: bool,
    ) -> UUID:
        return await self._catalog.upsert_product(
            local_id,
            iiko_id=iiko_id,
            name=name,
            article=article,
            base_unit=base_unit,
            category_id=category_id,
            archived=archived,
        )

    async def upsert_supplier(
        self,
        local_id: UUID | None,
        *,
        iiko_id: UUID,
        name: str,
        phone: str | None,
        inn: str | None,
        payment_method: PaymentMethod | None,
    ) -> UUID:
        return await self._catalog.upsert_supplier(
            local_id,
            iiko_id=iiko_id,
            name=name,
            phone=phone,
            inn=inn,
            payment_method=payment_method.value if payment_method else None,
        )

    async def record_purchase_price(
        self, *, supplier_id: UUID, product_id: UUID, price_per_base_unit: Decimal, on: date
    ) -> bool:
        return await self._catalog.record_purchase_price(
            supplier_id=supplier_id, product_id=product_id, price_per_base_unit=price_per_base_unit, on=on
        )
