from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.catalog.domain.supplier import PaymentTerms


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    inn: str | None
    payment_terms: PaymentTerms
    deferral_days: int
    credit_limit: Decimal
    archived: bool


class RegisterSupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    inn: str | None = Field(default=None, max_length=14)
    payment_terms: PaymentTerms
    deferral_days: int = Field(default=0, ge=0, le=120)
    credit_limit: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    min_order_amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)


class CreatedOut(BaseModel):
    id: UUID
