from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zakup.modules.finance.domain.finance import (
    InvalidPaymentError,
    Obligation,
    ObligationStatus,
    PaymentLine,
    PaymentMethod,
    PaymentPaid,
    PaymentRequest,
    PaymentStatus,
)
from zakup.modules.procurement.domain.approval import ApprovalLimitError, SupplierDebtPolicy, ensure_supplier_credit
from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.errors import InvalidTransitionError

AT = datetime(2026, 10, 4, 9, tzinfo=UTC)
SUPPLIER = uuid4()


def obligation(amount: str = "1000", *, blocked: bool = False, deferral: int = 7) -> Obligation:
    return Obligation.from_receipt(
        id=uuid4(),
        receipt_id=uuid4(),
        receipt_number="R-000001",
        supplier_id=SUPPLIER,
        store_id=uuid4(),
        amount=Decimal(amount),
        received_on=date(2026, 10, 1),
        deferral_days=deferral,
        blocked=blocked,
    )


def request(lines: list[PaymentLine], *, approval: bool = True) -> PaymentRequest:
    return PaymentRequest.create(
        id=uuid4(),
        number="P-000001",
        supplier_id=SUPPLIER,
        method=PaymentMethod.TRANSFER,
        lines=lines,
        requested_by=uuid4(),
        at=AT,
        comment=None,
        approval_required=approval,
    )


def test_due_date_and_overdue() -> None:
    item = obligation(deferral=7)
    assert item.due_date == date(2026, 10, 8)
    assert not item.is_overdue(date(2026, 10, 8))
    assert item.is_overdue(date(2026, 10, 9))
    assert not obligation(blocked=True, deferral=0).is_overdue(date(2026, 10, 9))  # nizo — muddat hisoblanmaydi


def test_partial_then_full_allocation() -> None:
    item = obligation("1000")
    item.allocate(Decimal(400))
    assert (item.status, item.outstanding) == (ObligationStatus.PARTIALLY_PAID, Decimal(600))
    with pytest.raises(InvalidPaymentError):
        item.allocate(Decimal(601))
    item.allocate(Decimal(600))
    assert item.status is ObligationStatus.PAID


def test_blocked_obligation_cannot_be_paid_until_accepted() -> None:
    item = obligation("1000", blocked=True)
    assert item.status is ObligationStatus.BLOCKED
    with pytest.raises(InvalidPaymentError, match="obligation_blocked"):
        item.allocate(Decimal(1))
    item.accept(Decimal(900))
    assert (item.status, item.amount) == (ObligationStatus.OPEN, Decimal(900))


def test_payment_request_lifecycle_allocates_to_invoices() -> None:
    first, second = obligation("1000"), obligation("500")
    payment = request([PaymentLine(first.id, Decimal(1000)), PaymentLine(second.id, Decimal(200))])
    assert (payment.status, payment.total) == (PaymentStatus.SUBMITTED, Decimal(1200))
    with pytest.raises(InvalidTransitionError):
        payment.pay({first.id: first, second.id: second}, by=uuid4(), at=AT, proof_id=None)
    payment.approve(by=uuid4(), at=AT)
    payment.pay({first.id: first, second.id: second}, by=uuid4(), at=AT, proof_id=None)
    assert payment.status is PaymentStatus.PAID
    assert (first.status, second.outstanding) == (ObligationStatus.PAID, Decimal(300))
    (event,) = payment.pull_events()
    assert isinstance(event, PaymentPaid)
    assert event.amount == "1200"


def test_payment_request_validation() -> None:
    line = PaymentLine(uuid4(), Decimal(1))
    with pytest.raises(InvalidPaymentError, match="no_lines"):
        request([])
    with pytest.raises(InvalidPaymentError, match="duplicate_line"):
        request([line, line])
    with pytest.raises(InvalidPaymentError, match="amount_invalid"):
        request([PaymentLine(uuid4(), Decimal(0))])
    assert request([line], approval=False).status is PaymentStatus.APPROVED
    with pytest.raises(InvalidPaymentError, match="comment_required"):
        request([line]).reject(by=uuid4(), comment=" ", at=AT)


@pytest.mark.parametrize(
    ("policy", "role", "allowed"),
    [
        (SupplierDebtPolicy.REQUIRE_ADMIN, Role.BUYER, False),
        (SupplierDebtPolicy.REQUIRE_ADMIN, Role.ADMIN, True),
        (SupplierDebtPolicy.BLOCK, Role.ADMIN, False),
        (SupplierDebtPolicy.OFF, Role.BUYER, True),
    ],
)
def test_supplier_debt_policy(policy: SupplierDebtPolicy, role: Role, allowed: bool) -> None:
    actor = Principal(uuid4(), frozenset({RoleGrant(role)}))
    if allowed:
        ensure_supplier_credit(actor, "overdue", policy, supplier="X")
    else:
        with pytest.raises(ApprovalLimitError, match="supplier_overdue"):
            ensure_supplier_credit(actor, "overdue", policy, supplier="X")
    ensure_supplier_credit(actor, None, policy, supplier="X")  # qarz yo'q — doim ruxsat
