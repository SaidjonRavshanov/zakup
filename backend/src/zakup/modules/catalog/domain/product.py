"""Tovar va kategoriya. Master — iiko (номенклатура); bu yerda qo'lda yaratish faqat iiko ulanmaguncha
yoki iiko'da hali yo'q tovar uchun (WORKFLOW B1, 16-bo'shliq)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id
from zakup.shared_kernel.money import Money

MAX_NAME = 300


class Unit(StrEnum):
    """O'lchov birligi kodi; iiko birliklari shu kodlarga moslanadi (frontend: shared/i18n/keys.ts UnitCode)."""

    KG = "kg"
    G = "g"
    L = "l"
    ML = "ml"
    PCS = "pcs"
    PACK = "pack"
    BOX = "box"
    BAG = "bag"


# Bazaviy birlik — ombor qoldig'i va sarf shu birlikda (qadoq birliklari — faqat yetkazib beruvchida)
BASE_UNITS = frozenset({Unit.KG, Unit.G, Unit.L, Unit.ML, Unit.PCS})


class InvalidProductError(DomainError):
    code = "invalid_product"


@dataclass(frozen=True, kw_only=True)
class ProductRegistered(DomainEvent):
    event_type: ClassVar[str] = "catalog.product_registered"
    name: str


@dataclass(frozen=True, kw_only=True)
class ProductArchived(DomainEvent):
    event_type: ClassVar[str] = "catalog.product_archived"


class ProductCategory(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.product_category"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        name: str,
        parent_id: UUID | None = None,
        monthly_budget: Money | None = None,
        iiko_id: UUID | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.parent_id = parent_id
        self.monthly_budget = monthly_budget
        self.iiko_id = iiko_id
        self.version = version

    @classmethod
    def create(cls, *, name: str, parent_id: UUID | None = None, monthly_budget: Money | None = None) -> Self:
        if monthly_budget is not None and monthly_budget.is_negative():
            raise InvalidProductError("category.budget_negative")
        return cls(
            id=new_id(),
            name=_clean_name(name, "category.name_empty"),
            parent_id=parent_id,
            monthly_budget=monthly_budget,
        )


class Product(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.product"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        name: str,
        article: str | None,
        base_unit: Unit,
        category_id: UUID | None,
        iiko_id: UUID | None = None,
        archived_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.article = article
        self.base_unit = base_unit
        self.category_id = category_id
        self.iiko_id = iiko_id
        self.archived_at = archived_at
        self.version = version

    @classmethod
    def register(
        cls,
        *,
        name: str,
        base_unit: Unit,
        article: str | None = None,
        category_id: UUID | None = None,
        iiko_id: UUID | None = None,
    ) -> Self:
        _check_base_unit(base_unit)
        product = cls(
            id=new_id(),
            name=_clean_name(name, "product.name_empty"),
            article=(article or "").strip() or None,
            base_unit=base_unit,
            category_id=category_id,
            iiko_id=iiko_id,
        )
        product.record(ProductRegistered(aggregate_id=product.id, name=product.name))
        return product

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def revise(self, *, name: str, article: str | None, base_unit: Unit, category_id: UUID | None) -> None:
        _check_base_unit(base_unit)
        self.name = _clean_name(name, "product.name_empty")
        self.article = (article or "").strip() or None
        self.base_unit = base_unit
        self.category_id = category_id

    def archive(self, at: datetime) -> None:
        """iiko'da o'chirilgan / yashirilgan → arxiv: yangi zayavkalarda yo'q, tarixda qoladi."""
        if self.is_archived:
            return
        self.archived_at = at
        self.record(ProductArchived(aggregate_id=self.id))


def _check_base_unit(unit: Unit) -> None:
    if unit not in BASE_UNITS:
        raise InvalidProductError("product.base_unit")


def _clean_name(name: str, empty_key: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise InvalidProductError(empty_key)
    if len(cleaned) > MAX_NAME:
        raise InvalidProductError("product.name_too_long", max=MAX_NAME)
    return cleaned
