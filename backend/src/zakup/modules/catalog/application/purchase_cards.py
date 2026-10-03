"""Xarid kartochkasi: tovar x ombor normativlari va yetkazib beruvchi tanlovi (WORKFLOW B3, B6)."""

from uuid import UUID

from zakup.modules.catalog.application.common import load
from zakup.modules.catalog.application.dto import PurchaseCardCommand
from zakup.modules.catalog.application.ports import (
    ProductRepository,
    PurchaseCardRepository,
    StoreRepository,
    SupplierRepository,
)
from zakup.modules.catalog.domain.purchase_card import InvalidPurchaseCardError, Norms, PurchaseCard, SupplierChoice
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.uow import UnitOfWork


class ConfigurePurchaseCard:
    """Kartochka bo'lmasa — ochiladi, bo'lsa — yangilanadi (tovar + ombor bo'yicha bitta)."""

    def __init__(
        self,
        uow: UnitOfWork,
        cards: PurchaseCardRepository,
        products: ProductRepository,
        stores: StoreRepository,
        suppliers: SupplierRepository,
    ) -> None:
        self._uow = uow
        self._cards = cards
        self._products = products
        self._stores = stores
        self._suppliers = suppliers

    async def __call__(self, actor: Principal, cmd: PurchaseCardCommand) -> UUID:
        actor.require(Role.BUYER, Role.ADMIN, store_id=cmd.store_id)
        async with self._uow:
            await load(self._products, cmd.product_id, "product.not_found")
            await load(self._stores, cmd.store_id, "store.not_found")
            for supplier_id in (cmd.primary_supplier_id, cmd.alternative_supplier_id):
                if supplier_id is not None:
                    await self._check_supplier(supplier_id)

            card = await self._cards.find(product_id=cmd.product_id, store_id=cmd.store_id)
            is_new = card is None
            if card is None:
                card = PurchaseCard.open(product_id=cmd.product_id, store_id=cmd.store_id)
            card.configure(
                mode=cmd.mode,
                norms=Norms(
                    safety_stock=cmd.safety_stock,
                    coverage_days=cmd.coverage_days,
                    shelf_life_days=cmd.shelf_life_days,
                    seasonal_factor=cmd.seasonal_factor,
                ),
                suppliers=SupplierChoice(cmd.primary_supplier_id, cmd.alternative_supplier_id),
            )
            await (self._cards.add(card) if is_new else self._cards.save(card))
            self._uow.track(card)
            await self._uow.commit()
            return card.id

    async def _check_supplier(self, supplier_id: UUID) -> None:
        supplier = await load(self._suppliers, supplier_id, "supplier.not_found")
        if supplier.is_archived:
            raise InvalidPurchaseCardError("card.supplier_archived")
