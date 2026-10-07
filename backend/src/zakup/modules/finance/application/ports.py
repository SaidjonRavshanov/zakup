"""finance port'lari. catalog bilan — faqat uning public interfeysi orqali (adapter)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from zakup.modules.finance.application.dto import ObligationView, PaymentDetail, PaymentListItem
from zakup.modules.finance.domain.finance import Obligation, PaymentRequest, PaymentStatus


class ObligationRepository(Protocol):
    async def by_receipt(self, receipt_id: UUID) -> Obligation | None: ...

    async def get_many(self, ids: Iterable[UUID]) -> dict[UUID, Obligation]:
        """Qatorlarni bloklab o'qiydi (FOR UPDATE): bir vaqtda ikki to'lov bitta nakladnoyni ortiqcha yopmasin."""

    async def add(self, obligation: Obligation) -> None: ...

    async def save(self, obligation: Obligation) -> None: ...


class PaymentRepository(Protocol):
    async def next_number(self) -> str: ...

    async def get(self, payment_id: UUID) -> PaymentRequest | None: ...

    async def add(self, payment: PaymentRequest) -> None: ...

    async def save(self, payment: PaymentRequest) -> None: ...

    async def reserved(self, obligation_ids: Iterable[UUID], *, exclude: UUID | None = None) -> dict[UUID, Decimal]:
        """Faol (SUBMITTED / APPROVED) zayavkalarda band summa — nakladnoy bo'yicha."""


@dataclass(frozen=True, slots=True)
class PaymentTerms:
    name: str
    deferral_days: int
    credit_limit: Decimal  # 0 — limit yo'q


class SuppliersPort(Protocol):
    async def terms(self, supplier_id: UUID) -> PaymentTerms | None: ...

    async def labels(
        self, *, suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> tuple[dict[UUID, str], dict[UUID, str]]:
        """(yetkazuvchilar, omborlar) nomlari."""


class FinanceReader(Protocol):
    async def obligations(
        self, *, supplier_id: UUID | None, store_ids: set[UUID] | None, unpaid_only: bool
    ) -> list[ObligationView]: ...

    async def payments(
        self,
        *,
        statuses: set[PaymentStatus] | None,
        supplier_id: UUID | None,
        limit: int,
        store_ids: set[UUID] | None = None,
    ) -> list[PaymentListItem]:
        """store_ids — faqat shu omborlar nakladnoylari bor zayavkalar (None — hammasi)."""
        ...

    async def payment(self, payment_id: UUID, store_ids: set[UUID] | None = None) -> PaymentDetail | None: ...


class StoredFile(Protocol):
    """Fayl ombori umumiy (receiving bilan bitta jadval) — shuning uchun tuzilma bo'yicha (Protocol)."""

    @property
    def content_type(self) -> str: ...

    @property
    def content(self) -> bytes: ...


class Attachments(Protocol):
    """To'lov tasdig'i (chek, bank ko'chirmasi): hozir lokal disk, keyin S3."""

    async def store(self, *, content: bytes, content_type: str, uploaded_by: UUID, at: datetime) -> UUID: ...

    async def exists(self, file_id: UUID) -> bool: ...

    async def load(self, file_id: UUID) -> StoredFile | None: ...
