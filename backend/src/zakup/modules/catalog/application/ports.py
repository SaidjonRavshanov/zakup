"""Catalog moduli port'lari — implementatsiyalar infrastructure qatlamida (DIP, ISP)."""

from typing import Protocol, TypeVar
from uuid import UUID

from zakup.modules.catalog.application.dto import (
    CategoryItem,
    PriceHistoryItem,
    ProductDetail,
    ProductListItem,
    StoreItem,
    SupplierDetail,
    SupplierListItem,
)
from zakup.modules.catalog.domain.branch import Branch
from zakup.modules.catalog.domain.offer import PriceRecord, SupplierOffer
from zakup.modules.catalog.domain.product import Product, ProductCategory
from zakup.modules.catalog.domain.purchase_card import PurchaseCard
from zakup.modules.catalog.domain.store import Store
from zakup.modules.catalog.domain.supplier import Supplier

A = TypeVar("A")


class Repository(Protocol[A]):
    """Yozish tomoni: aggregate'ni to'liq yuklaydi/saqlaydi. `save` — optimistic lock (ConflictError)."""

    async def get(self, entity_id: UUID) -> A | None: ...

    async def add(self, entity: A) -> None: ...

    async def save(self, entity: A) -> None: ...


class SupplierRepository(Repository[Supplier], Protocol):
    async def exists_by_inn(self, inn: str, *, exclude_id: UUID | None = None) -> bool: ...


class StoreRepository(Repository[Store], Protocol): ...


class BranchRepository(Repository[Branch], Protocol): ...


class CategoryRepository(Repository[ProductCategory], Protocol): ...


class ProductRepository(Repository[Product], Protocol):
    async def find_by_article(self, article: str) -> Product | None: ...


class OfferRepository(Repository[SupplierOffer], Protocol):
    async def exists(self, *, supplier_id: UUID, product_id: UUID, supplier_sku: str | None) -> bool: ...

    async def find(self, *, supplier_id: UUID, product_id: UUID, supplier_sku: str | None) -> SupplierOffer | None: ...


class PriceHistory(Protocol):
    async def append(self, record: PriceRecord) -> None: ...


class PurchaseCardRepository(Repository[PurchaseCard], Protocol):
    async def find(self, *, product_id: UUID, store_id: UUID) -> PurchaseCard | None: ...


class SupplierReader(Protocol):
    """O'qish tomoni (CQRS-lite): to'g'ridan-to'g'ri DTO, aggregate yaratilmaydi."""

    async def list(self, *, include_archived: bool, search: str | None, limit: int) -> list[SupplierListItem]: ...

    async def detail(self, supplier_id: UUID) -> SupplierDetail | None: ...


class StoreReader(Protocol):
    async def list(self, *, include_archived: bool) -> list[StoreItem]: ...


class CategoryReader(Protocol):
    async def list(self) -> list[CategoryItem]: ...


class ProductReader(Protocol):
    async def list(
        self, *, include_archived: bool, search: str | None, category_id: UUID | None, limit: int
    ) -> list[ProductListItem]: ...

    async def detail(self, product_id: UUID) -> ProductDetail | None: ...


class PriceHistoryReader(Protocol):
    async def history(self, offer_id: UUID, *, limit: int) -> list[PriceHistoryItem]: ...
