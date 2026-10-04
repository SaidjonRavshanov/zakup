from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.domain.offer import PriceSource
from zakup.modules.catalog.domain.product import Unit
from zakup.modules.catalog.domain.purchase_card import PurchaseMode
from zakup.modules.catalog.domain.supplier import WEEKDAYS, PaymentTerms

_ALL_DAYS = tuple(sorted(WEEKDAYS))

# ---------------------------------------------------------------- yetkazib beruvchi


@dataclass(frozen=True, slots=True)
class SupplierListItem:
    id: UUID
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int
    credit_limit: Decimal
    archived: bool
    payment_methods: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContactsData:
    phone: str | None = None
    telegram: str | None = None
    email: str | None = None
    person: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterSupplierCommand:
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int = 0
    credit_limit: Decimal = Decimal(0)
    min_order_amount: Decimal = Decimal(0)
    lead_time_days: int = 1
    order_weekdays: tuple[int, ...] = _ALL_DAYS
    delivery_weekdays: tuple[int, ...] = _ALL_DAYS
    order_cutoff: time | None = None
    contacts: ContactsData = field(default_factory=ContactsData)


@dataclass(frozen=True, slots=True)
class SupplierDetail:
    id: UUID
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int
    credit_limit: Decimal
    min_order_amount: Decimal
    lead_time_days: int
    order_weekdays: tuple[int, ...]
    delivery_weekdays: tuple[int, ...]
    order_cutoff: time | None
    contacts: ContactsData
    archived: bool
    version: int
    payment_methods: tuple[str, ...] = ()
    offers: tuple["OfferItem", ...] = ()


# ---------------------------------------------------------------- ombor, kategoriya, tovar


@dataclass(frozen=True, slots=True)
class StoreItem:
    id: UUID
    name: str
    address: str | None
    from_iiko: bool
    archived: bool
    branch_id: UUID | None = None
    branch_name: str | None = None


@dataclass(frozen=True, slots=True)
class CategoryItem:
    id: UUID
    name: str
    parent_id: UUID | None
    monthly_budget: Decimal | None


@dataclass(frozen=True, slots=True)
class ProductCommand:
    name: str
    base_unit: Unit
    article: str | None = None
    category_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProductListItem:
    id: UUID
    name: str
    article: str | None
    base_unit: Unit
    category_id: UUID | None
    category_name: str | None
    offers_count: int
    from_iiko: bool
    archived: bool


@dataclass(frozen=True, slots=True)
class ProductDetail:
    id: UUID
    name: str
    article: str | None
    base_unit: Unit
    category_id: UUID | None
    category_name: str | None
    from_iiko: bool
    archived: bool
    offers: tuple["OfferItem", ...]
    cards: tuple["PurchaseCardItem", ...]


# ---------------------------------------------------------------- taklif va narx


@dataclass(frozen=True, slots=True)
class OfferCommand:
    pack_unit: Unit
    pack_factor: Decimal
    order_multiple: Decimal = Decimal(1)
    supplier_sku: str | None = None
    supplier_product_name: str | None = None


@dataclass(frozen=True, slots=True)
class OfferItem:
    id: UUID
    supplier_id: UUID
    supplier_name: str
    product_id: UUID
    product_name: str
    base_unit: Unit
    supplier_sku: str | None
    supplier_product_name: str | None
    pack_unit: Unit
    pack_factor: Decimal
    order_multiple: Decimal
    price: Decimal
    base_unit_price: Decimal
    price_valid_from: date
    archived: bool


@dataclass(frozen=True, slots=True)
class PriceHistoryItem:
    price: Decimal
    valid_from: date
    source: PriceSource
    created_at: datetime


# ---------------------------------------------------------------- xarid kartochkasi


@dataclass(frozen=True, slots=True)
class PurchaseCardCommand:
    product_id: UUID
    store_id: UUID
    mode: PurchaseMode
    safety_stock: Decimal = Decimal(0)
    coverage_days: int = 7
    shelf_life_days: int | None = None
    seasonal_factor: Decimal = Decimal(1)
    primary_supplier_id: UUID | None = None
    alternative_supplier_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PurchaseCardItem:
    id: UUID
    product_id: UUID
    store_id: UUID
    store_name: str
    mode: PurchaseMode
    safety_stock: Decimal
    coverage_days: int
    shelf_life_days: int | None
    seasonal_factor: Decimal
    primary_supplier_id: UUID | None
    primary_supplier_name: str | None
    alternative_supplier_id: UUID | None
    alternative_supplier_name: str | None


@dataclass(frozen=True, slots=True)
class Labels:
    """ID → ko'rinadigan nom (boshqa modullar ro'yxatlari uchun)."""

    products: dict[UUID, tuple[str, Unit]]  # (nom, bazaviy birlik)
    suppliers: dict[UUID, str]
    stores: dict[UUID, str]
