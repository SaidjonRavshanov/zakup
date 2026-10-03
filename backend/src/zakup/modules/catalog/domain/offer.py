"""Yetkazib beruvchi taklifi: "bizning tovar ↔ yetkazib beruvchi tovari" mosligi (WORKFLOW 17-bo'shliq),
qadoq (1 qop = 25 kg, 1-bo'shliq), karralilik va narx (qadoq uchun)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.modules.catalog.domain.product import Unit
from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id

PRICE_EXP = Decimal("0.0001")  # narx (birlik uchun) — numeric(18,4), DATABASE §1
QTY_EXP = Decimal("0.0001")
MAX_SKU = 100


class PriceSource(StrEnum):
    MANUAL = "manual"
    IIKO = "iiko"
    SUPPLIER_RESPONSE = "supplier_response"
    RECEIPT = "receipt"


class InvalidOfferError(DomainError):
    code = "invalid_offer"


class DuplicateOfferError(DomainError):
    code = "duplicate_offer"


@dataclass(frozen=True, slots=True)
class Packaging:
    """`unit` — yetkazib beruvchi birligi, `factor` — bitta qadoqda nechta bazaviy birlik,
    `multiple` — necha qadoqqa karrali buyurtma qilinadi (1.3 qop bo'lmaydi)."""

    unit: Unit
    factor: Decimal
    multiple: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        if not self.factor.is_finite() or self.factor <= 0:
            raise InvalidOfferError("offer.factor_positive")
        if not self.multiple.is_finite() or self.multiple <= 0:
            raise InvalidOfferError("offer.multiple_positive")
        object.__setattr__(self, "factor", self.factor.quantize(QTY_EXP, ROUND_HALF_UP))
        object.__setattr__(self, "multiple", self.multiple.quantize(QTY_EXP, ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class OrderQuantity:
    packs: Decimal
    base_qty: Decimal


@dataclass(frozen=True, slots=True)
class PriceRecord:
    """Narx tarixi yozuvi (supplier_price_history) — narx dinamikasi va reyting uchun (WORKFLOW B14)."""

    offer_id: UUID
    price: Decimal
    valid_from: date
    source: PriceSource


@dataclass(frozen=True, kw_only=True)
class OfferPriceChanged(DomainEvent):
    event_type: ClassVar[str] = "catalog.offer_price_changed"
    old_price: str
    new_price: str
    source: str


class SupplierOffer(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.supplier_offer"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        supplier_id: UUID,
        product_id: UUID,
        supplier_sku: str | None,
        supplier_name: str | None,
        packaging: Packaging,
        price: Decimal,
        price_valid_from: date,
        archived_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.supplier_id = supplier_id
        self.product_id = product_id
        self.supplier_sku = supplier_sku
        self.supplier_name = supplier_name
        self.packaging = packaging
        self.price = price
        self.price_valid_from = price_valid_from
        self.archived_at = archived_at
        self.version = version

    @classmethod
    def create(
        cls,
        *,
        supplier_id: UUID,
        product_id: UUID,
        packaging: Packaging,
        price: Decimal,
        valid_from: date,
        supplier_sku: str | None = None,
        supplier_name: str | None = None,
    ) -> tuple[Self, PriceRecord]:
        offer = cls(
            id=new_id(),
            supplier_id=supplier_id,
            product_id=product_id,
            supplier_sku=_clean_sku(supplier_sku),
            supplier_name=(supplier_name or "").strip() or None,
            packaging=packaging,
            price=_check_price(price),
            price_valid_from=valid_from,
        )
        return offer, PriceRecord(offer.id, offer.price, valid_from, PriceSource.MANUAL)

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    @property
    def base_unit_price(self) -> Decimal:
        """Bazaviy birlik narxi — turli qadoqdagi takliflarni solishtirish uchun (WORKFLOW B6)."""
        return (self.price / self.packaging.factor).quantize(PRICE_EXP, ROUND_HALF_UP)

    def revise(self, *, supplier_sku: str | None, supplier_name: str | None, packaging: Packaging) -> None:
        self.supplier_sku = _clean_sku(supplier_sku)
        self.supplier_name = (supplier_name or "").strip() or None
        self.packaging = packaging

    def change_price(self, price: Decimal, valid_from: date, source: PriceSource) -> PriceRecord | None:
        price = _check_price(price)
        if price == self.price and valid_from == self.price_valid_from:
            return None
        if valid_from < self.price_valid_from:
            raise InvalidOfferError("offer.price_backdated")
        old = self.price
        self.price = price
        self.price_valid_from = valid_from
        self.record(OfferPriceChanged(aggregate_id=self.id, old_price=str(old), new_price=str(price), source=source))
        return PriceRecord(self.id, price, valid_from, source)

    def order_quantity(self, need_base_qty: Decimal) -> OrderQuantity:
        """Ehtiyoj (bazaviy birlikda) → yuqoriga karralilikkacha yaxlitlangan qadoqlar (WORKFLOW B3 formulasi)."""
        if need_base_qty <= 0:
            return OrderQuantity(Decimal(0), Decimal(0))
        step = self.packaging.multiple
        steps = (need_base_qty / self.packaging.factor / step).to_integral_value(ROUND_CEILING)
        packs = steps * step
        return OrderQuantity(packs=packs, base_qty=(packs * self.packaging.factor).quantize(QTY_EXP, ROUND_HALF_UP))

    def archive(self, at: datetime) -> None:
        self.archived_at = self.archived_at or at


def _check_price(price: Decimal) -> Decimal:
    if not price.is_finite() or price < 0:
        raise InvalidOfferError("offer.price_negative")
    return price.quantize(PRICE_EXP, ROUND_HALF_UP)


def _clean_sku(sku: str | None) -> str | None:
    sku = (sku or "").strip() or None
    if sku and len(sku) > MAX_SKU:
        raise InvalidOfferError("offer.sku_too_long", max=MAX_SKU)
    return sku
