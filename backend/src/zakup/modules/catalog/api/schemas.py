from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.catalog.application.dto import (
    ContactsData,
    OfferCommand,
    ProductCommand,
    PurchaseCardCommand,
    RegisterSupplierCommand,
)
from zakup.modules.catalog.domain.offer import PriceSource
from zakup.modules.catalog.domain.product import Unit
from zakup.modules.catalog.domain.purchase_card import PurchaseMode
from zakup.modules.catalog.domain.supplier import PaymentTerms

Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]
Price = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
Qty = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
Weekday = Annotated[int, Field(ge=1, le=7)]
_ALL_DAYS = [1, 2, 3, 4, 5, 6, 7]


class CreatedOut(BaseModel):
    id: UUID


# ---------------------------------------------------------------- yetkazib beruvchi


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int
    credit_limit: Decimal
    archived: bool


class ContactsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone: str | None = Field(default=None, max_length=20)
    telegram: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    person: str | None = Field(default=None, max_length=200)


class RegisterSupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    inn: str | None = Field(default=None, max_length=14)
    payment_terms: PaymentTerms
    deferral_days: int = Field(default=0, ge=0, le=120)
    credit_limit: Money = Decimal(0)
    min_order_amount: Money = Decimal(0)
    lead_time_days: int = Field(default=1, ge=0, le=60)
    order_weekdays: list[Weekday] = Field(default_factory=lambda: list(_ALL_DAYS), min_length=1, max_length=7)
    delivery_weekdays: list[Weekday] = Field(default_factory=lambda: list(_ALL_DAYS), min_length=1, max_length=7)
    order_cutoff: time | None = None
    contacts: ContactsSchema = Field(default_factory=ContactsSchema)

    def to_command(self) -> RegisterSupplierCommand:
        data = self.model_dump(exclude={"contacts", "order_weekdays", "delivery_weekdays"})
        return RegisterSupplierCommand(
            **data,
            order_weekdays=tuple(self.order_weekdays),
            delivery_weekdays=tuple(self.delivery_weekdays),
            contacts=ContactsData(**self.contacts.model_dump()),
        )


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class SupplierDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int
    credit_limit: Decimal
    min_order_amount: Decimal
    lead_time_days: int
    order_weekdays: list[int]
    delivery_weekdays: list[int]
    order_cutoff: time | None
    contacts: ContactsSchema
    archived: bool
    offers: list[OfferOut]


# ---------------------------------------------------------------- ombor, kategoriya, tovar


class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None
    from_iiko: bool
    archived: bool


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: UUID | None = None
    monthly_budget: Money | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None
    monthly_budget: Decimal | None


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    base_unit: Unit
    article: str | None = Field(default=None, max_length=100)
    category_id: UUID | None = None

    def to_command(self) -> ProductCommand:
        return ProductCommand(**self.model_dump())


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    article: str | None
    base_unit: Unit
    category_id: UUID | None
    category_name: str | None
    offers_count: int
    from_iiko: bool
    archived: bool


class PurchaseCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ProductDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    article: str | None
    base_unit: Unit
    category_id: UUID | None
    category_name: str | None
    from_iiko: bool
    archived: bool
    offers: list[OfferOut]
    cards: list[PurchaseCardOut]


# ---------------------------------------------------------------- taklif, narx, kartochka


_OFFER_FIELDS = {"pack_unit", "pack_factor", "order_multiple", "supplier_sku", "supplier_product_name"}


class OfferIn(BaseModel):
    pack_unit: Unit
    pack_factor: Qty
    order_multiple: Qty = Decimal(1)
    supplier_sku: str | None = Field(default=None, max_length=100)
    supplier_product_name: str | None = Field(default=None, max_length=300)
    price: Price

    def to_command(self) -> OfferCommand:
        return OfferCommand(**self.model_dump(include=_OFFER_FIELDS))


class NewOfferIn(OfferIn):
    product_id: UUID


class ReviseOfferIn(OfferIn):
    # Bo'sh — bugungi sana (Toshkent); o'tgan sanaga surish taqiqlangan (domen tekshiradi)
    price_valid_from: date | None = None


class PriceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: Decimal
    valid_from: date
    source: PriceSource
    created_at: datetime


class PurchaseCardIn(BaseModel):
    product_id: UUID
    store_id: UUID
    mode: PurchaseMode
    safety_stock: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)] = Decimal(0)
    coverage_days: int = Field(default=7, ge=1, le=90)
    shelf_life_days: int | None = Field(default=None, ge=1, le=3650)
    seasonal_factor: Annotated[Decimal, Field(ge=Decimal("0.1"), le=5, decimal_places=3)] = Decimal(1)
    primary_supplier_id: UUID | None = None
    alternative_supplier_id: UUID | None = None

    def to_command(self) -> PurchaseCardCommand:
        return PurchaseCardCommand(**self.model_dump())
