"""iikoServer (iikoRMS 9.x) javoblarining sof modeli — HTTP / XML / JSON'dan mustaqil.

Tarnov tarmog'i (2026-10, Sebzar namunasi):
- har bir filialda o'z iikoRMS serveri; bo'limlar (department) va omborlar ma'lumotnomasi —
  **butun tarmoq uchun umumiy**
  (har server 5 filialning 100 omborini qaytaradi), qoldiq va nakladnoylar — faqat o'z filiali bo'yicha;
- tovar turlari: GOODS (xarid qilinadi), PREPARED (yarim tayyor), DISH, SERVICE, MODIFIER, OUTER — bizga faqat GOODS.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class DepartmentType(StrEnum):
    CORPORATION = "CORPORATION"
    JURPERSON = "JURPERSON"
    DEPARTMENT = "DEPARTMENT"


@dataclass(frozen=True, slots=True)
class IikoDepartment:
    id: UUID
    name: str
    code: str | None
    type: DepartmentType


@dataclass(frozen=True, slots=True)
class IikoStore:
    id: UUID
    name: str
    department_id: UUID | None


@dataclass(frozen=True, slots=True)
class IikoUnit:
    id: UUID
    name: str
    code: str | None


@dataclass(frozen=True, slots=True)
class IikoProductGroup:
    id: UUID
    name: str
    parent_id: UUID | None
    deleted: bool


@dataclass(frozen=True, slots=True)
class IikoContainer:
    """iiko'dagi qadoq: "Blok = 12 dona" — yetkazib beruvchi qadog'i uchun maslahat."""

    id: UUID
    name: str
    count: Decimal


@dataclass(frozen=True, slots=True)
class IikoProduct:
    id: UUID
    name: str
    article: str | None  # iiko "num" — nakladnoydagi productArticle bilan bir xil
    type: str
    unit_id: UUID | None
    group_id: UUID | None
    deleted: bool
    containers: tuple[IikoContainer, ...] = ()


@dataclass(frozen=True, slots=True)
class IikoSupplier:
    id: UUID
    name: str
    code: str | None
    phone: str | None
    inn: str | None
    deleted: bool
    # "Tarnov Chorsu: Bar ombori" — filiallar orasidagi ko'chirish uchun ombor-kontragent, haqiqiy yetkazuvchi emas
    represents_store: bool = False


@dataclass(frozen=True, slots=True)
class IikoInvoiceItem:
    product_id: UUID
    store_id: UUID | None
    amount: Decimal  # mahsulotning asosiy birligida
    price: Decimal  # asosiy birlik narxi
    total: Decimal
    container_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class IikoIncomingInvoice:
    id: UUID
    number: str | None
    incoming_date: date
    supplier_id: UUID | None
    store_id: UUID | None
    status: str  # PROCESSED (o'tkazilgan) | NEW
    comment: str | None
    items: tuple[IikoInvoiceItem, ...] = field(default=())

    @property
    def is_processed(self) -> bool:
        return self.status == "PROCESSED"
