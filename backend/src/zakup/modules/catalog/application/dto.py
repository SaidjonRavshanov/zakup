from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.domain.supplier import PaymentTerms


@dataclass(frozen=True, slots=True)
class SupplierListItem:
    id: UUID
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int
    credit_limit: Decimal
    archived: bool


@dataclass(frozen=True, slots=True)
class RegisterSupplierCommand:
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int = 0
    credit_limit: Decimal = Decimal(0)
    min_order_amount: Decimal = Decimal(0)
