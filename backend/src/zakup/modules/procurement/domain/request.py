"""Zayavka (PurchaseRequest) — WORKFLOW B4, B5; status mashinasi — ARCHITECTURE §5.

    DRAFT → PENDING_APPROVAL → APPROVED | PARTIALLY_APPROVED → SPLIT (PO'larga bo'lindi)
                │   └── qaytarildi (izoh bilan) → DRAFT
                └──► REJECTED                     CANCELLED (SPLIT gacha)

Miqdor — tovarning bazaviy birligida (oshpaz kg / dona bilan o'ylaydi); qadoqqa aylantirish — PO'da.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.modules.procurement.domain.approval import ApprovalPolicy, ApprovalRecord, Decision
from zakup.shared_kernel.auth import Principal
from zakup.shared_kernel.errors import DomainError, InvalidTransitionError, NotFoundError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id

MAX_LINES = 300
MAX_NOTE = 500
QTY_EXP = Decimal("0.0001")
MONEY_EXP = Decimal("0.01")


class RequestStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    SPLIT = "SPLIT"


class RequestType(StrEnum):
    MANUAL = "manual"
    EVENT = "event"  # banket / tadbir: o'rtacha sarf normasiga ta'sir qilmaydi (WORKFLOW 4в)
    AUTO = "auto"


class LineDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InvalidRequestError(DomainError):
    code = "invalid_request"


@dataclass(frozen=True, slots=True)
class OfferChoice:
    """Tanlangan yetkazuvchi taklifi: kutilgan narx — bazaviy birlik uchun (taklif narxi / qadoqdagi miqdor)."""

    offer_id: UUID
    supplier_id: UUID
    price_per_base: Decimal


@dataclass(slots=True)
class RequestLine:
    id: UUID
    product_id: UUID
    qty: Decimal
    note: str | None = None
    offer: OfferChoice | None = None
    decision: LineDecision = LineDecision.PENDING

    @property
    def expected_amount(self) -> Decimal:
        if self.offer is None:
            return Decimal(0)
        return (self.qty * self.offer.price_per_base).quantize(MONEY_EXP, ROUND_HALF_UP)


@dataclass(frozen=True, kw_only=True)
class RequestSubmitted(DomainEvent):
    event_type: ClassVar[str] = "procurement.request_submitted"
    store_id: str
    amount: str


@dataclass(frozen=True, kw_only=True)
class RequestDecided(DomainEvent):
    event_type: ClassVar[str] = "procurement.request_decided"
    decision: str
    approver_id: str
    role_conflict: bool


class PurchaseRequest(AggregateRoot):
    aggregate_type: ClassVar[str] = "procurement.purchase_request"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        number: str,
        store_id: UUID,
        type: RequestType,  # noqa: A002
        status: RequestStatus,
        needed_by: date,
        initiator_id: UUID,
        comment: str | None = None,
        lines: list[RequestLine] | None = None,
        approvals: list[ApprovalRecord] | None = None,
        submitted_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.number = number
        self.store_id = store_id
        self.type = type
        self.status = status
        self.needed_by = needed_by
        self.initiator_id = initiator_id
        self.comment = comment
        self.lines = lines or []
        self.approvals = approvals or []
        self.submitted_at = submitted_at
        self.version = version
        self._new_approvals: list[ApprovalRecord] = []

    # ------------------------------------------------------------ yaratish va tahrir (DRAFT)

    @classmethod
    def create(
        cls,
        *,
        number: str,
        store_id: UUID,
        initiator: Principal,
        needed_by: date,
        today: date,
        type: RequestType = RequestType.MANUAL,  # noqa: A002
        comment: str | None = None,
    ) -> Self:
        _check_needed_by(needed_by, today)
        return cls(
            id=new_id(),
            number=number,
            store_id=store_id,
            type=type,
            status=RequestStatus.DRAFT,
            needed_by=needed_by,
            initiator_id=initiator.user_id,
            comment=_clean(comment),
        )

    def revise(self, *, needed_by: date, comment: str | None, today: date) -> None:
        self._require(RequestStatus.DRAFT)
        _check_needed_by(needed_by, today)
        self.needed_by = needed_by
        self.comment = _clean(comment)

    def add_line(self, *, product_id: UUID, qty: Decimal, note: str | None, offer: OfferChoice | None) -> RequestLine:
        self._require(RequestStatus.DRAFT)
        if any(line.product_id == product_id for line in self.lines):
            raise InvalidRequestError("request.duplicate_product")
        if len(self.lines) >= MAX_LINES:
            raise InvalidRequestError("request.too_many_lines", max=MAX_LINES)
        line = RequestLine(id=new_id(), product_id=product_id, qty=_check_qty(qty), note=_clean(note), offer=offer)
        self.lines.append(line)
        return line

    def change_line(self, line_id: UUID, *, qty: Decimal, note: str | None) -> None:
        self._require(RequestStatus.DRAFT)
        line = self._line(line_id)
        line.qty = _check_qty(qty)
        line.note = _clean(note)

    def remove_line(self, line_id: UUID) -> None:
        self._require(RequestStatus.DRAFT)
        self.lines.remove(self._line(line_id))

    def choose_offer(self, line_id: UUID, offer: OfferChoice | None) -> None:
        """Yetkazuvchini zakupshik tasdiqlashgacha o'zgartira oladi (DRAFT yoki PENDING_APPROVAL)."""
        self._require(RequestStatus.DRAFT, RequestStatus.PENDING_APPROVAL)
        self._line(line_id).offer = offer

    # ------------------------------------------------------------ jarayon

    def submit(self, *, today: date, at: datetime) -> None:
        self._require(RequestStatus.DRAFT)
        if not self.lines:
            raise InvalidRequestError("request.empty")
        _check_needed_by(self.needed_by, today)
        for line in self.lines:
            line.decision = LineDecision.PENDING
        self.status = RequestStatus.PENDING_APPROVAL
        self.submitted_at = at
        self.record(RequestSubmitted(aggregate_id=self.id, store_id=str(self.store_id), amount=str(self.total)))

    def approve(
        self, actor: Principal, policy: ApprovalPolicy, *, at: datetime, line_ids: set[UUID] | None = None
    ) -> None:
        """`line_ids=None` — hammasi; aks holda qisman: qolganlari rad etiladi."""
        self._require(RequestStatus.PENDING_APPROVAL)
        approved = [line for line in self.lines if line_ids is None or line.id in line_ids]
        if not approved:
            raise InvalidRequestError("request.nothing_approved")
        if line_ids is not None and len(approved) != len(line_ids):
            raise NotFoundError("request.line_not_found")
        if any(line.offer is None for line in approved):
            raise InvalidRequestError("request.line_without_supplier")
        amount = sum((line.expected_amount for line in approved), Decimal(0))
        policy.ensure_can_approve(actor, self.store_id, amount)

        for line in self.lines:
            line.decision = LineDecision.APPROVED if line in approved else LineDecision.REJECTED
        partial = len(approved) < len(self.lines)
        self.status = RequestStatus.PARTIALLY_APPROVED if partial else RequestStatus.APPROVED
        self._decide(actor, Decision.PARTIAL if partial else Decision.APPROVED, None, amount, at)

    def return_to_draft(self, actor: Principal, *, comment: str, at: datetime) -> None:
        self._require(RequestStatus.PENDING_APPROVAL)
        self._decide(actor, Decision.RETURNED, _required_comment(comment), self.total, at)
        self.status = RequestStatus.DRAFT

    def reject(self, actor: Principal, *, comment: str, at: datetime) -> None:
        self._require(RequestStatus.PENDING_APPROVAL)
        self._decide(actor, Decision.REJECTED, _required_comment(comment), self.total, at)
        for line in self.lines:
            line.decision = LineDecision.REJECTED
        self.status = RequestStatus.REJECTED

    def cancel(self) -> None:
        self._require(
            RequestStatus.DRAFT,
            RequestStatus.PENDING_APPROVAL,
            RequestStatus.APPROVED,
            RequestStatus.PARTIALLY_APPROVED,
        )
        self.status = RequestStatus.CANCELLED

    def mark_split(self) -> None:
        self._require(RequestStatus.APPROVED, RequestStatus.PARTIALLY_APPROVED)
        self.status = RequestStatus.SPLIT

    # ------------------------------------------------------------ hisob

    @property
    def total(self) -> Decimal:
        return sum((line.expected_amount for line in self.lines), Decimal(0))

    @property
    def approved_lines(self) -> list[RequestLine]:
        return [line for line in self.lines if line.decision is LineDecision.APPROVED]

    def pull_new_approvals(self) -> list[ApprovalRecord]:
        new, self._new_approvals = self._new_approvals, []
        return new

    # ------------------------------------------------------------ ichki

    def _decide(self, actor: Principal, decision: Decision, comment: str | None, amount: Decimal, at: datetime) -> None:
        record = ApprovalRecord(
            approver_id=actor.user_id,
            decision=decision,
            comment=comment,
            amount=amount,
            role_conflict=actor.user_id == self.initiator_id,  # tasdiqlovchi ≠ tashabbuskor (WORKFLOW 2)
            decided_at=at,
        )
        self.approvals.append(record)
        self._new_approvals.append(record)
        self.record(
            RequestDecided(
                aggregate_id=self.id,
                decision=decision.value,
                approver_id=str(actor.user_id),
                role_conflict=record.role_conflict,
            )
        )

    def _require(self, *allowed: RequestStatus) -> None:
        if self.status not in allowed:
            raise InvalidTransitionError("request.invalid_status", status=self.status.value)

    def _line(self, line_id: UUID) -> RequestLine:
        for line in self.lines:
            if line.id == line_id:
                return line
        raise NotFoundError("request.line_not_found")


def _check_qty(qty: Decimal) -> Decimal:
    if not qty.is_finite() or qty <= 0:
        raise InvalidRequestError("request.qty_positive")
    return qty.quantize(QTY_EXP, ROUND_HALF_UP)


def _check_needed_by(needed_by: date, today: date) -> None:
    if needed_by < today:
        raise InvalidRequestError("request.needed_by_past")


def _clean(text: str | None) -> str | None:
    cleaned = " ".join((text or "").split())[:MAX_NOTE]
    return cleaned or None


def _required_comment(comment: str) -> str:
    cleaned = _clean(comment)
    if not cleaned:
        raise InvalidRequestError("request.comment_required")
    return cleaned
