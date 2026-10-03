"""Xarid kartochkasi (карточка закупа) — tovar x ombor normativlari (WORKFLOW B3).

Yangi tovar default "faqat qo'lda": avto-zakupda qatnashmaydi, toki normativ va asosiy yetkazib beruvchi berilmaguncha.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id

MAX_COVERAGE_DAYS = 90
MIN_SEASONAL, MAX_SEASONAL = Decimal("0.1"), Decimal(5)


class PurchaseMode(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"
    DISABLED = "disabled"


class InvalidPurchaseCardError(DomainError):
    code = "invalid_purchase_card"


@dataclass(frozen=True, slots=True)
class Norms:
    safety_stock: Decimal = Decimal(0)  # bazaviy birlikda
    coverage_days: int = 7
    shelf_life_days: int | None = None
    seasonal_factor: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        if not self.safety_stock.is_finite() or self.safety_stock < 0:
            raise InvalidPurchaseCardError("card.safety_stock_negative")
        if not 1 <= self.coverage_days <= MAX_COVERAGE_DAYS:
            raise InvalidPurchaseCardError("card.coverage_range", max=MAX_COVERAGE_DAYS)
        if self.shelf_life_days is not None and self.shelf_life_days < 1:
            raise InvalidPurchaseCardError("card.shelf_life_positive")
        if not MIN_SEASONAL <= self.seasonal_factor <= MAX_SEASONAL:
            raise InvalidPurchaseCardError("card.seasonal_range", min=MIN_SEASONAL, max=MAX_SEASONAL)


@dataclass(frozen=True, slots=True)
class SupplierChoice:
    primary_id: UUID | None = None
    alternative_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.alternative_id and not self.primary_id:
            raise InvalidPurchaseCardError("card.alternative_without_primary")
        if self.primary_id and self.primary_id == self.alternative_id:
            raise InvalidPurchaseCardError("card.same_suppliers")


@dataclass(frozen=True, kw_only=True)
class PurchaseCardChanged(DomainEvent):
    event_type: ClassVar[str] = "catalog.purchase_card_changed"
    product_id: str
    store_id: str
    mode: str


class PurchaseCard(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.purchase_card"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        product_id: UUID,
        store_id: UUID,
        mode: PurchaseMode,
        norms: Norms,
        suppliers: SupplierChoice,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.product_id = product_id
        self.store_id = store_id
        self.mode = mode
        self.norms = norms
        self.suppliers = suppliers
        self.version = version

    @classmethod
    def open(cls, *, product_id: UUID, store_id: UUID) -> Self:
        return cls(
            id=new_id(),
            product_id=product_id,
            store_id=store_id,
            mode=PurchaseMode.MANUAL,
            norms=Norms(),
            suppliers=SupplierChoice(),
        )

    def configure(self, *, mode: PurchaseMode, norms: Norms, suppliers: SupplierChoice) -> None:
        if mode is PurchaseMode.AUTO and suppliers.primary_id is None:
            raise InvalidPurchaseCardError("card.auto_needs_supplier")
        self.mode = mode
        self.norms = norms
        self.suppliers = suppliers
        self.record(
            PurchaseCardChanged(
                aggregate_id=self.id, product_id=str(self.product_id), store_id=str(self.store_id), mode=mode
            )
        )

    def effective_coverage_days(self, lead_time_days: int) -> int:
        """Tez buziladigan tovar: qoplash davri ≤ yaroqlilik - yetkazish muddati (WORKFLOW B3)."""
        coverage = self.norms.coverage_days
        if self.norms.shelf_life_days is not None:
            coverage = min(coverage, self.norms.shelf_life_days - lead_time_days)
        return max(coverage, 0)
