"""Tovarlar va kategoriyalar."""

from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.application.common import load, page_size
from zakup.modules.catalog.application.dto import CategoryItem, ProductCommand, ProductDetail, ProductListItem
from zakup.modules.catalog.application.ports import (
    CategoryReader,
    CategoryRepository,
    ProductReader,
    ProductRepository,
)
from zakup.modules.catalog.domain.product import Product, ProductCategory
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.errors import NotFoundError
from zakup.shared_kernel.money import Money
from zakup.shared_kernel.uow import UnitOfWork

EDITORS = (Role.BUYER, Role.ADMIN)


class CreateCategory:
    def __init__(self, uow: UnitOfWork, categories: CategoryRepository) -> None:
        self._uow = uow
        self._categories = categories

    async def __call__(
        self, actor: Principal, *, name: str, parent_id: UUID | None, monthly_budget: Decimal | None
    ) -> UUID:
        actor.require(Role.ADMIN)
        async with self._uow:
            if parent_id is not None:
                await load(self._categories, parent_id, "category.not_found")
            category = ProductCategory.create(
                name=name,
                parent_id=parent_id,
                monthly_budget=Money(monthly_budget) if monthly_budget is not None else None,
            )
            await self._categories.add(category)
            await self._uow.commit()
            return category.id


class ListCategories:
    def __init__(self, reader: CategoryReader) -> None:
        self._reader = reader

    async def __call__(self) -> list[CategoryItem]:
        return await self._reader.list()


class RegisterProduct:
    def __init__(self, uow: UnitOfWork, products: ProductRepository, categories: CategoryRepository) -> None:
        self._uow = uow
        self._products = products
        self._categories = categories

    async def __call__(self, actor: Principal, cmd: ProductCommand) -> UUID:
        actor.require(*EDITORS)
        async with self._uow:
            if cmd.category_id is not None:
                await load(self._categories, cmd.category_id, "category.not_found")
            product = Product.register(
                name=cmd.name, base_unit=cmd.base_unit, article=cmd.article, category_id=cmd.category_id
            )
            await self._products.add(product)
            self._uow.track(product)
            await self._uow.commit()
            return product.id


class ReviseProduct:
    def __init__(self, uow: UnitOfWork, products: ProductRepository, categories: CategoryRepository) -> None:
        self._uow = uow
        self._products = products
        self._categories = categories

    async def __call__(self, actor: Principal, product_id: UUID, cmd: ProductCommand) -> None:
        actor.require(*EDITORS)
        async with self._uow:
            product = await load(self._products, product_id, "product.not_found")
            if cmd.category_id is not None:
                await load(self._categories, cmd.category_id, "category.not_found")
            product.revise(name=cmd.name, article=cmd.article, base_unit=cmd.base_unit, category_id=cmd.category_id)
            await self._products.save(product)
            await self._uow.commit()


class ArchiveProduct:
    def __init__(self, uow: UnitOfWork, products: ProductRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._products = products
        self._clock = clock

    async def __call__(self, actor: Principal, product_id: UUID) -> None:
        actor.require(*EDITORS)
        async with self._uow:
            product = await load(self._products, product_id, "product.not_found")
            product.archive(self._clock())
            await self._products.save(product)
            self._uow.track(product)
            await self._uow.commit()


class ListProducts:
    def __init__(self, reader: ProductReader) -> None:
        self._reader = reader

    async def __call__(
        self,
        *,
        include_archived: bool = False,
        search: str | None = None,
        category_id: UUID | None = None,
        limit: int = 50,
    ) -> list[ProductListItem]:
        return await self._reader.list(
            include_archived=include_archived,
            search=search.strip() if search else None,
            category_id=category_id,
            limit=page_size(limit),
        )


class GetProduct:
    def __init__(self, reader: ProductReader) -> None:
        self._reader = reader

    async def __call__(self, product_id: UUID) -> ProductDetail:
        detail = await self._reader.detail(product_id)
        if detail is None:
            raise NotFoundError("product.not_found")
        return detail
