"""O'qish tomoni (CQRS-lite, ADR-03): faqat kerakli ustunlar → DTO, ORM hydratsiyasiz."""

from decimal import ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from zakup.modules.catalog.application.dto import (
    CategoryItem,
    ContactsData,
    OfferItem,
    PriceHistoryItem,
    ProductDetail,
    ProductListItem,
    PurchaseCardItem,
    StoreItem,
    SupplierDetail,
    SupplierListItem,
)
from zakup.modules.catalog.domain.offer import PRICE_EXP, PriceSource
from zakup.modules.catalog.domain.product import Unit
from zakup.modules.catalog.domain.purchase_card import PurchaseMode
from zakup.modules.catalog.domain.supplier import PaymentTerms
from zakup.modules.catalog.infrastructure.tables import (
    product_categories,
    products,
    purchase_cards,
    stores,
    supplier_price_history,
    supplier_products,
    suppliers,
)


def _offers_query() -> Select[Any]:
    return (
        select(
            supplier_products,
            suppliers.c.name.label("supplier_company"),
            products.c.name.label("product_name"),
            products.c.base_unit,
        )
        .join(suppliers, suppliers.c.id == supplier_products.c.supplier_id)
        .join(products, products.c.id == supplier_products.c.product_id)
        .order_by(
            supplier_products.c.archived_at.is_not(None), supplier_products.c.price / supplier_products.c.pack_factor
        )
    )


def _offer_item(row: Row[Any]) -> OfferItem:
    return OfferItem(
        id=row.id,
        supplier_id=row.supplier_id,
        supplier_name=row.supplier_company,
        product_id=row.product_id,
        product_name=row.product_name,
        base_unit=Unit(row.base_unit),
        supplier_sku=row.supplier_sku,
        supplier_product_name=row.supplier_name,
        pack_unit=Unit(row.pack_unit),
        pack_factor=row.pack_factor,
        order_multiple=row.order_multiple,
        price=row.price,
        base_unit_price=(row.price / row.pack_factor).quantize(PRICE_EXP, ROUND_HALF_UP),
        price_valid_from=row.price_valid_from,
        archived=row.archived_at is not None,
    )


async def _offers(session: AsyncSession, condition: ColumnElement[bool]) -> tuple[OfferItem, ...]:
    rows = (await session.execute(_offers_query().where(condition))).all()
    return tuple(_offer_item(row) for row in rows)


class SqlSupplierReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, include_archived: bool, search: str | None, limit: int) -> list[SupplierListItem]:
        query = select(
            suppliers.c.id,
            suppliers.c.name,
            suppliers.c.inn,
            suppliers.c.payment_terms,
            suppliers.c.deferral_days,
            suppliers.c.credit_limit,
            suppliers.c.archived_at,
        ).order_by(suppliers.c.name, suppliers.c.id)
        if not include_archived:
            query = query.where(suppliers.c.archived_at.is_(None))
        if search:
            query = query.where(suppliers.c.name.icontains(search, autoescape=True) | (suppliers.c.inn == search))
        rows = (await self._session.execute(query.limit(limit))).all()
        return [
            SupplierListItem(
                id=row.id,
                name=row.name,
                inn=row.inn,
                payment_terms=PaymentTerms(row.payment_terms),
                deferral_days=row.deferral_days,
                credit_limit=row.credit_limit,
                archived=row.archived_at is not None,
            )
            for row in rows
        ]

    async def detail(self, supplier_id: UUID) -> SupplierDetail | None:
        row = (await self._session.execute(select(suppliers).where(suppliers.c.id == supplier_id))).first()
        if row is None:
            return None
        return SupplierDetail(
            id=row.id,
            name=row.name,
            inn=row.inn,
            payment_terms=PaymentTerms(row.payment_terms),
            deferral_days=row.deferral_days,
            credit_limit=row.credit_limit,
            min_order_amount=row.min_order_amount,
            lead_time_days=row.lead_time_days,
            order_weekdays=tuple(sorted(row.order_weekdays)),
            delivery_weekdays=tuple(sorted(row.delivery_weekdays)),
            order_cutoff=row.order_cutoff,
            contacts=ContactsData(**row.contacts),
            archived=row.archived_at is not None,
            version=row.version,
            offers=await _offers(self._session, supplier_products.c.supplier_id == supplier_id),
        )


class SqlStoreReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, include_archived: bool) -> list[StoreItem]:
        query = select(stores).order_by(stores.c.name, stores.c.id)
        if not include_archived:
            query = query.where(stores.c.archived_at.is_(None))
        rows = (await self._session.execute(query)).all()
        return [
            StoreItem(
                id=row.id,
                name=row.name,
                address=row.address,
                from_iiko=row.iiko_id is not None,
                archived=row.archived_at is not None,
            )
            for row in rows
        ]


class SqlCategoryReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[CategoryItem]:
        query = select(product_categories).order_by(product_categories.c.name, product_categories.c.id)
        rows = (await self._session.execute(query)).all()
        return [
            CategoryItem(id=row.id, name=row.name, parent_id=row.parent_id, monthly_budget=row.monthly_budget)
            for row in rows
        ]


class SqlProductReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, include_archived: bool, search: str | None, category_id: UUID | None, limit: int
    ) -> list[ProductListItem]:
        offers_count = (
            select(func.count())
            .where(supplier_products.c.product_id == products.c.id, supplier_products.c.archived_at.is_(None))
            .scalar_subquery()
        )
        query = (
            select(products, product_categories.c.name.label("category_name"), offers_count.label("offers_count"))
            .outerjoin(product_categories, product_categories.c.id == products.c.category_id)
            .order_by(products.c.name, products.c.id)
        )
        if not include_archived:
            query = query.where(products.c.archived_at.is_(None))
        if category_id is not None:
            query = query.where(products.c.category_id == category_id)
        if search:
            query = query.where(products.c.name.icontains(search, autoescape=True) | (products.c.article == search))
        rows = (await self._session.execute(query.limit(limit))).all()
        return [
            ProductListItem(
                id=row.id,
                name=row.name,
                article=row.article,
                base_unit=Unit(row.base_unit),
                category_id=row.category_id,
                category_name=row.category_name,
                offers_count=row.offers_count,
                from_iiko=row.iiko_id is not None,
                archived=row.archived_at is not None,
            )
            for row in rows
        ]

    async def detail(self, product_id: UUID) -> ProductDetail | None:
        query = (
            select(products, product_categories.c.name.label("category_name"))
            .outerjoin(product_categories, product_categories.c.id == products.c.category_id)
            .where(products.c.id == product_id)
        )
        row = (await self._session.execute(query)).first()
        if row is None:
            return None
        return ProductDetail(
            id=row.id,
            name=row.name,
            article=row.article,
            base_unit=Unit(row.base_unit),
            category_id=row.category_id,
            category_name=row.category_name,
            from_iiko=row.iiko_id is not None,
            archived=row.archived_at is not None,
            offers=await _offers(self._session, supplier_products.c.product_id == product_id),
            cards=await self._cards(product_id),
        )

    async def _cards(self, product_id: UUID) -> tuple[PurchaseCardItem, ...]:
        primary, alternative = aliased(suppliers), aliased(suppliers)
        query = (
            select(
                purchase_cards,
                stores.c.name.label("store_name"),
                primary.c.name.label("primary_name"),
                alternative.c.name.label("alternative_name"),
            )
            .join(stores, stores.c.id == purchase_cards.c.store_id)
            .outerjoin(primary, primary.c.id == purchase_cards.c.primary_supplier_id)
            .outerjoin(alternative, alternative.c.id == purchase_cards.c.alternative_supplier_id)
            .where(purchase_cards.c.product_id == product_id)
            .order_by(stores.c.name)
        )
        rows = (await self._session.execute(query)).all()
        return tuple(
            PurchaseCardItem(
                id=row.id,
                product_id=row.product_id,
                store_id=row.store_id,
                store_name=row.store_name,
                mode=PurchaseMode(row.mode),
                safety_stock=row.safety_stock,
                coverage_days=row.coverage_days,
                shelf_life_days=row.shelf_life_days,
                seasonal_factor=row.seasonal_factor,
                primary_supplier_id=row.primary_supplier_id,
                primary_supplier_name=row.primary_name,
                alternative_supplier_id=row.alternative_supplier_id,
                alternative_supplier_name=row.alternative_name,
            )
            for row in rows
        )


class SqlPriceHistoryReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def history(self, offer_id: UUID, *, limit: int) -> list[PriceHistoryItem]:
        query = (
            select(supplier_price_history)
            .where(supplier_price_history.c.supplier_product_id == offer_id)
            .order_by(supplier_price_history.c.valid_from.desc(), supplier_price_history.c.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(query)).all()
        return [
            PriceHistoryItem(
                price=row.price, valid_from=row.valid_from, source=PriceSource(row.source), created_at=row.created_at
            )
            for row in rows
        ]
