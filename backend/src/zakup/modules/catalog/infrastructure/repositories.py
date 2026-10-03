"""Yozish tomoni: aggregate ↔ jadval qatori. Hammasi bitta jadvalli, `version` bilan optimistic lock."""

from collections.abc import Callable
from typing import Any, ClassVar, Protocol
from uuid import UUID

from sqlalchemy import Table, exists, func, insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.catalog.domain.branch import Branch
from zakup.modules.catalog.domain.offer import Packaging, PriceRecord, SupplierOffer
from zakup.modules.catalog.domain.product import Product, ProductCategory, Unit
from zakup.modules.catalog.domain.purchase_card import Norms, PurchaseCard, PurchaseMode, SupplierChoice
from zakup.modules.catalog.domain.store import Store
from zakup.modules.catalog.domain.supplier import Contacts, OrderSchedule, PaymentMethod, PaymentTerms, Supplier
from zakup.modules.catalog.infrastructure.tables import (
    branches,
    product_categories,
    products,
    purchase_cards,
    stores,
    supplier_price_history,
    supplier_products,
    suppliers,
)
from zakup.shared_kernel.errors import ConflictError
from zakup.shared_kernel.ids import new_id
from zakup.shared_kernel.money import Money


class Versioned(Protocol):
    id: UUID
    version: int


class _TableRepository[A: Versioned]:
    table: ClassVar[Table]
    conflict_key: ClassVar[str]
    to_row: Callable[[A], dict[str, Any]]
    to_domain: Callable[[RowMapping], A]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> A | None:
        row = (await self._session.execute(select(self.table).where(self.table.c.id == entity_id))).mappings().first()
        return type(self).to_domain(row) if row else None

    async def add(self, entity: A) -> None:
        await self._session.execute(
            insert(self.table).values(id=entity.id, version=entity.version, **type(self).to_row(entity))
        )

    async def save(self, entity: A) -> None:
        result = await self._session.execute(
            update(self.table)
            .where(self.table.c.id == entity.id, self.table.c.version == entity.version)
            .values(**type(self).to_row(entity), version=entity.version + 1, updated_at=func.now())
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError(self.conflict_key)
        entity.version += 1


# ---------------------------------------------------------------- supplier


def _supplier_row(supplier: Supplier) -> dict[str, Any]:
    contacts = supplier.contacts
    return {
        "iiko_id": supplier.iiko_id,
        "name": supplier.name,
        "inn": supplier.inn,
        "payment_terms": supplier.payment_terms.value,
        "deferral_days": supplier.deferral_days,
        "credit_limit": supplier.credit_limit.amount,
        "min_order_amount": supplier.min_order_amount.amount,
        "currency": supplier.credit_limit.currency,
        "lead_time_days": supplier.schedule.lead_time_days,
        "order_weekdays": sorted(supplier.schedule.order_weekdays),
        "delivery_weekdays": sorted(supplier.schedule.delivery_weekdays),
        "order_cutoff": supplier.schedule.order_cutoff,
        "contacts": {k: v for k, v in _contacts_dict(contacts).items() if v},
        "payment_methods": sorted(m.value for m in supplier.payment_methods),
        "archived_at": supplier.archived_at,
    }


def _contacts_dict(contacts: Contacts) -> dict[str, str | None]:
    return {"phone": contacts.phone, "telegram": contacts.telegram, "email": contacts.email, "person": contacts.person}


def _supplier(row: RowMapping) -> Supplier:
    return Supplier(
        id=row["id"],
        iiko_id=row["iiko_id"],
        name=row["name"],
        inn=row["inn"],
        payment_terms=PaymentTerms(row["payment_terms"]),
        deferral_days=row["deferral_days"],
        credit_limit=Money(row["credit_limit"], row["currency"]),
        min_order_amount=Money(row["min_order_amount"], row["currency"]),
        schedule=OrderSchedule(
            lead_time_days=row["lead_time_days"],
            order_weekdays=frozenset(row["order_weekdays"]),
            delivery_weekdays=frozenset(row["delivery_weekdays"]),
            order_cutoff=row["order_cutoff"],
        ),
        contacts=Contacts(**row["contacts"]),
        payment_methods=frozenset(PaymentMethod(m) for m in row["payment_methods"]),
        archived_at=row["archived_at"],
        version=row["version"],
    )


class SqlSupplierRepository(_TableRepository[Supplier]):
    table = suppliers
    conflict_key = "supplier.modified"
    to_row = staticmethod(_supplier_row)
    to_domain = staticmethod(_supplier)

    async def exists_by_inn(self, inn: str, *, exclude_id: UUID | None = None) -> bool:
        condition = (suppliers.c.inn == inn) & suppliers.c.archived_at.is_(None)
        if exclude_id is not None:
            condition &= suppliers.c.id != exclude_id
        return bool(await self._session.scalar(select(exists().where(condition))))


# ---------------------------------------------------------------- store, category, product


class SqlStoreRepository(_TableRepository[Store]):
    table = stores
    conflict_key = "store.modified"
    to_row = staticmethod(
        lambda s: {
            "iiko_id": s.iiko_id,
            "branch_id": s.branch_id,
            "name": s.name,
            "address": s.address,
            "archived_at": s.archived_at,
        }
    )
    to_domain = staticmethod(
        lambda r: Store(
            id=r["id"],
            iiko_id=r["iiko_id"],
            name=r["name"],
            address=r["address"],
            branch_id=r["branch_id"],
            archived_at=r["archived_at"],
            version=r["version"],
        )
    )


class SqlBranchRepository(_TableRepository[Branch]):
    table = branches
    conflict_key = "branch.modified"
    to_row = staticmethod(
        lambda b: {"iiko_id": b.iiko_id, "code": b.code, "name": b.name, "archived_at": b.archived_at}
    )
    to_domain = staticmethod(
        lambda r: Branch(
            id=r["id"],
            iiko_id=r["iiko_id"],
            code=r["code"],
            name=r["name"],
            archived_at=r["archived_at"],
            version=r["version"],
        )
    )


class SqlCategoryRepository(_TableRepository[ProductCategory]):
    table = product_categories
    conflict_key = "category.modified"
    to_row = staticmethod(
        lambda c: {
            "iiko_id": c.iiko_id,
            "parent_id": c.parent_id,
            "name": c.name,
            "monthly_budget": c.monthly_budget.amount if c.monthly_budget else None,
        }
    )
    to_domain = staticmethod(
        lambda r: ProductCategory(
            id=r["id"],
            iiko_id=r["iiko_id"],
            parent_id=r["parent_id"],
            name=r["name"],
            monthly_budget=Money(r["monthly_budget"]) if r["monthly_budget"] is not None else None,
            version=r["version"],
        )
    )


class SqlProductRepository(_TableRepository[Product]):
    async def find_by_article(self, article: str) -> Product | None:
        query = select(products).where(products.c.article == article).order_by(products.c.archived_at.is_not(None))
        row = (await self._session.execute(query.limit(1))).mappings().first()
        return type(self).to_domain(row) if row else None

    table = products
    conflict_key = "product.modified"
    to_row = staticmethod(
        lambda p: {
            "iiko_id": p.iiko_id,
            "name": p.name,
            "article": p.article,
            "base_unit": p.base_unit.value,
            "category_id": p.category_id,
            "archived_at": p.archived_at,
        }
    )
    to_domain = staticmethod(
        lambda r: Product(
            id=r["id"],
            iiko_id=r["iiko_id"],
            name=r["name"],
            article=r["article"],
            base_unit=Unit(r["base_unit"]),
            category_id=r["category_id"],
            archived_at=r["archived_at"],
            version=r["version"],
        )
    )


# ---------------------------------------------------------------- offer, price history, purchase card


def _offer_row(offer: SupplierOffer) -> dict[str, Any]:
    return {
        "supplier_id": offer.supplier_id,
        "product_id": offer.product_id,
        "supplier_sku": offer.supplier_sku,
        "supplier_name": offer.supplier_name,
        "pack_unit": offer.packaging.unit.value,
        "pack_factor": offer.packaging.factor,
        "order_multiple": offer.packaging.multiple,
        "price": offer.price,
        "price_valid_from": offer.price_valid_from,
        "archived_at": offer.archived_at,
    }


def _offer(row: RowMapping) -> SupplierOffer:
    return SupplierOffer(
        id=row["id"],
        supplier_id=row["supplier_id"],
        product_id=row["product_id"],
        supplier_sku=row["supplier_sku"],
        supplier_name=row["supplier_name"],
        packaging=Packaging(Unit(row["pack_unit"]), row["pack_factor"], row["order_multiple"]),
        price=row["price"],
        price_valid_from=row["price_valid_from"],
        archived_at=row["archived_at"],
        version=row["version"],
    )


class SqlOfferRepository(_TableRepository[SupplierOffer]):
    table = supplier_products
    conflict_key = "offer.modified"
    to_row = staticmethod(_offer_row)
    to_domain = staticmethod(_offer)

    async def find(self, *, supplier_id: UUID, product_id: UUID, supplier_sku: str | None) -> SupplierOffer | None:
        sku = supplier_products.c.supplier_sku
        query = select(supplier_products).where(
            supplier_products.c.supplier_id == supplier_id,
            supplier_products.c.product_id == product_id,
            sku.is_(None) if supplier_sku is None else sku == supplier_sku,
        )
        row = (await self._session.execute(query)).mappings().first()
        return _offer(row) if row else None

    async def exists(self, *, supplier_id: UUID, product_id: UUID, supplier_sku: str | None) -> bool:
        sku = supplier_products.c.supplier_sku
        condition = (
            (supplier_products.c.supplier_id == supplier_id)
            & (supplier_products.c.product_id == product_id)
            & (sku.is_(None) if supplier_sku is None else sku == supplier_sku)
        )
        return bool(await self._session.scalar(select(exists().where(condition))))


class SqlPriceHistory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, record: PriceRecord) -> None:
        await self._session.execute(
            insert(supplier_price_history).values(
                id=new_id(),
                supplier_product_id=record.offer_id,
                price=record.price,
                valid_from=record.valid_from,
                source=record.source.value,
            )
        )


def _card_row(card: PurchaseCard) -> dict[str, Any]:
    return {
        "product_id": card.product_id,
        "store_id": card.store_id,
        "mode": card.mode.value,
        "safety_stock": card.norms.safety_stock,
        "coverage_days": card.norms.coverage_days,
        "shelf_life_days": card.norms.shelf_life_days,
        "seasonal_factor": card.norms.seasonal_factor,
        "primary_supplier_id": card.suppliers.primary_id,
        "alternative_supplier_id": card.suppliers.alternative_id,
    }


def _card(row: RowMapping) -> PurchaseCard:
    return PurchaseCard(
        id=row["id"],
        product_id=row["product_id"],
        store_id=row["store_id"],
        mode=PurchaseMode(row["mode"]),
        norms=Norms(
            safety_stock=row["safety_stock"],
            coverage_days=row["coverage_days"],
            shelf_life_days=row["shelf_life_days"],
            seasonal_factor=row["seasonal_factor"],
        ),
        suppliers=SupplierChoice(row["primary_supplier_id"], row["alternative_supplier_id"]),
        version=row["version"],
    )


class SqlPurchaseCardRepository(_TableRepository[PurchaseCard]):
    table = purchase_cards
    conflict_key = "card.modified"
    to_row = staticmethod(_card_row)
    to_domain = staticmethod(_card)

    async def find(self, *, product_id: UUID, store_id: UUID) -> PurchaseCard | None:
        query = select(purchase_cards).where(
            purchase_cards.c.product_id == product_id, purchase_cards.c.store_id == store_id
        )
        row = (await self._session.execute(query)).mappings().first()
        return _card(row) if row else None
