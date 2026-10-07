"""To'lov use case'lari (WORKFLOW B12). Ruxsat — ombor doirasida (ARCHITECTURE §7).

Rollar: buxgalter zayavka tuzadi va to'laydi; tasdiqlovchi tasdiqlaydi (sozlamada o'chirsa bo'ladi);
admin — hammasi. Ko'rish: + zakupshik, auditor.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from zakup.modules.finance.application.dto import (
    CreatePaymentCommand,
    ObligationView,
    PaymentDetail,
    PaymentListItem,
    SupplierAccount,
    SupplierBalance,
)
from zakup.modules.finance.application.ports import (
    Attachments,
    FinanceReader,
    ObligationRepository,
    PaymentRepository,
    StoredFile,
    SuppliersPort,
)
from zakup.modules.finance.domain.finance import (
    InvalidPaymentError,
    Obligation,
    ObligationStatus,
    PaymentLine,
    PaymentRequest,
    PaymentStatus,
)
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, business_today, utc_now
from zakup.shared_kernel.errors import NotFoundError
from zakup.shared_kernel.ids import new_id
from zakup.shared_kernel.uow import UnitOfWork

PAYERS = (Role.ACCOUNTANT, Role.ADMIN)
APPROVERS = (Role.APPROVER, Role.ADMIN)
VIEWERS = (Role.ACCOUNTANT, Role.APPROVER, Role.BUYER, Role.AUDITOR, Role.ADMIN)
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "application/pdf"})
ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class FinanceSettings:
    payment_approval_required: bool = True


def _store_scope(actor: Principal, roles: Iterable[Role]) -> set[UUID] | None:
    """None — barcha omborlar."""
    grants = [g for g in actor.grants if g.role in set(roles)]
    if any(g.store_id is None for g in grants):
        return None
    return {g.store_id for g in grants if g.store_id}


# ---------------------------------------------------------------- majburiyat (event handler)


class RegisterObligation:
    """`receiving.receipt_*` event'i → majburiyat. Takroriy event — xavfsiz (receipt_id bo'yicha bitta).

    Tranzaksiyani outbox relay boshqaradi (handler bilan bitta savepoint).
    """

    def __init__(self, obligations: ObligationRepository, suppliers: SuppliersPort) -> None:
        self._obligations = obligations
        self._suppliers = suppliers

    async def __call__(
        self,
        *,
        receipt_id: UUID,
        receipt_number: str,
        supplier_id: UUID,
        store_id: UUID,
        amount: Decimal,
        received_at: datetime,
        blocked: bool,
    ) -> None:
        existing = await self._obligations.by_receipt(receipt_id)
        if existing is not None:
            if not blocked and existing.blocked:
                existing.accept(amount)
                await self._obligations.save(existing)
            return
        terms = await self._suppliers.terms(supplier_id)
        obligation = Obligation.from_receipt(
            id=new_id(),
            receipt_id=receipt_id,
            receipt_number=receipt_number,
            supplier_id=supplier_id,
            store_id=store_id,
            amount=amount,
            received_on=business_today(lambda: received_at),
            deferral_days=terms.deferral_days if terms else 0,
            blocked=blocked,
        )
        await self._obligations.add(obligation)


# ---------------------------------------------------------------- saldo


def _balance(
    supplier_id: UUID, items: list[ObligationView], name: str | None, credit_limit: Decimal | None
) -> SupplierBalance:
    debt = sum((o.outstanding for o in items if o.status is not ObligationStatus.BLOCKED), ZERO)
    blocked = sum((o.outstanding for o in items if o.status is ObligationStatus.BLOCKED), ZERO)
    payable = [o for o in items if o.status is not ObligationStatus.BLOCKED and o.outstanding > 0]
    limit = credit_limit if credit_limit and credit_limit > 0 else None
    return SupplierBalance(
        supplier_id=supplier_id,
        supplier_name=name,
        debt=debt,
        blocked=blocked,
        overdue=sum((o.outstanding for o in items if o.overdue), ZERO),
        reserved=sum((o.reserved for o in items), ZERO),
        credit_limit=limit,
        free_limit=limit - debt - blocked if limit is not None else None,
        nearest_due=min((o.due_date for o in payable), default=None),
        open_count=len([o for o in items if o.outstanding > 0]),
    )


class _Accounts:
    def __init__(self, reader: FinanceReader, payments: PaymentRepository, suppliers: SuppliersPort) -> None:
        self._reader = reader
        self._payments = payments
        self._suppliers = suppliers

    async def views(
        self, *, today: date, supplier_id: UUID | None, store_ids: set[UUID] | None
    ) -> list[ObligationView]:
        items = await self._reader.obligations(supplier_id=supplier_id, store_ids=store_ids, unpaid_only=True)
        reserved = await self._payments.reserved(o.id for o in items)
        _, stores = await self._suppliers.labels(stores={o.store_id for o in items})
        return [
            replace(
                o,
                overdue=o.status is not ObligationStatus.BLOCKED and o.due_date < today,
                reserved=reserved.get(o.id, ZERO),
                store_name=stores.get(o.store_id),
            )
            for o in items
        ]

    async def balance(self, supplier_id: UUID, items: list[ObligationView], name: str | None) -> SupplierBalance:
        terms = await self._suppliers.terms(supplier_id)
        return _balance(
            supplier_id, items, name or (terms.name if terms else None), terms.credit_limit if terms else None
        )


class ListBalances:
    def __init__(
        self, reader: FinanceReader, payments: PaymentRepository, suppliers: SuppliersPort, clock: Clock = utc_now
    ) -> None:
        self._accounts = _Accounts(reader, payments, suppliers)
        self._suppliers = suppliers
        self._clock = clock

    async def __call__(self, actor: Principal) -> list[SupplierBalance]:
        actor.require(*VIEWERS)
        views = await self._accounts.views(
            today=business_today(self._clock), supplier_id=None, store_ids=_store_scope(actor, VIEWERS)
        )
        by_supplier: dict[UUID, list[ObligationView]] = defaultdict(list)
        for view in views:
            by_supplier[view.supplier_id].append(view)
        names, _ = await self._suppliers.labels(suppliers=by_supplier)
        balances = [await self._accounts.balance(sid, items, names.get(sid)) for sid, items in by_supplier.items()]
        return sorted(balances, key=lambda b: (-b.overdue, -b.debt))


class GetSupplierAccount:
    def __init__(
        self, reader: FinanceReader, payments: PaymentRepository, suppliers: SuppliersPort, clock: Clock = utc_now
    ) -> None:
        self._accounts = _Accounts(reader, payments, suppliers)
        self._clock = clock

    async def __call__(self, actor: Principal, supplier_id: UUID) -> SupplierAccount:
        actor.require(*VIEWERS)
        views = await self._accounts.views(
            today=business_today(self._clock), supplier_id=supplier_id, store_ids=_store_scope(actor, VIEWERS)
        )
        views.sort(key=lambda o: (o.due_date, o.receipt_number))
        return SupplierAccount(balance=await self._accounts.balance(supplier_id, views, None), obligations=tuple(views))


class SupplierCredit:
    """procurement uchun public facade (bootstrap ulaydi): yangi buyurtma oldidan yetkazuvchi qarzi tekshiruvi.

    Natija — sabab kaliti yoki None: `overdue` (muddati o'tgan qarz bor), `over_limit` (kredit limiti yetmaydi).
    """

    def __init__(self, reader: FinanceReader, suppliers: SuppliersPort, clock: Clock = utc_now) -> None:
        self._reader = reader
        self._suppliers = suppliers
        self._clock = clock

    async def check(self, supplier_id: UUID, amount: Decimal) -> str | None:
        items = await self._reader.obligations(supplier_id=supplier_id, store_ids=None, unpaid_only=True)
        today = business_today(self._clock)
        if any(o.status is not ObligationStatus.BLOCKED and o.due_date < today for o in items):
            return "overdue"
        terms = await self._suppliers.terms(supplier_id)
        if terms and terms.credit_limit > 0:
            exposure = sum((o.outstanding for o in items), ZERO)
            if exposure + amount > terms.credit_limit:
                return "over_limit"
        return None


# ---------------------------------------------------------------- to'lov zayavkasi


async def _load(payments: PaymentRepository, payment_id: UUID) -> PaymentRequest:
    payment = await payments.get(payment_id)
    if payment is None:
        raise NotFoundError("payment.not_found")
    return payment


def _require_stores(actor: Principal, roles: tuple[Role, ...], obligations: Iterable[Obligation]) -> None:
    for obligation in obligations:
        actor.require(*roles, store_id=obligation.store_id)


class CreatePayment:
    def __init__(
        self,
        uow: UnitOfWork,
        payments: PaymentRepository,
        obligations: ObligationRepository,
        settings: FinanceSettings,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._payments = payments
        self._obligations = obligations
        self._settings = settings
        self._clock = clock

    async def __call__(self, actor: Principal, cmd: CreatePaymentCommand) -> UUID:
        actor.require(*PAYERS)
        async with self._uow:
            ids = [line.obligation_id for line in cmd.lines]
            found = await self._obligations.get_many(ids)
            reserved = await self._payments.reserved(ids)
            for line in cmd.lines:
                obligation = found.get(line.obligation_id)
                if obligation is None or obligation.supplier_id != cmd.supplier_id:
                    raise InvalidPaymentError("payment.obligation_not_found")
                if obligation.blocked:
                    raise InvalidPaymentError("payment.obligation_blocked", number=obligation.receipt_number)
                if line.amount > obligation.outstanding - reserved.get(obligation.id, ZERO):
                    raise InvalidPaymentError("payment.over_outstanding", number=obligation.receipt_number)
            _require_stores(actor, PAYERS, found.values())
            payment = PaymentRequest.create(
                id=new_id(),
                number=await self._payments.next_number(),
                supplier_id=cmd.supplier_id,
                method=cmd.method,
                lines=[PaymentLine(line.obligation_id, line.amount) for line in cmd.lines],
                requested_by=actor.user_id,
                at=self._clock(),
                comment=cmd.comment,
                approval_required=self._settings.payment_approval_required,
            )
            await self._payments.add(payment)
            self._uow.track(payment)
            await self._uow.commit()
            return payment.id


async def _require_payment_stores(
    actor: Principal, roles: tuple[Role, ...], payment: PaymentRequest, obligations: ObligationRepository
) -> None:
    """Bitta omborli xodim boshqa ombor nakladnoylari bo'yicha to'lovni tasdiqlay / bekor qila olmasin."""
    found = await obligations.get_many(line.obligation_id for line in payment.lines)
    _require_stores(actor, roles, found.values())


class ApprovePayment:
    def __init__(
        self, uow: UnitOfWork, payments: PaymentRepository, obligations: ObligationRepository, clock: Clock = utc_now
    ) -> None:
        self._uow = uow
        self._payments = payments
        self._obligations = obligations
        self._clock = clock

    async def __call__(self, actor: Principal, payment_id: UUID) -> None:
        actor.require(*APPROVERS)
        async with self._uow:
            payment = await _load(self._payments, payment_id)
            await _require_payment_stores(actor, APPROVERS, payment, self._obligations)
            payment.approve(by=actor.user_id, at=self._clock())
            await self._payments.save(payment)
            self._uow.track(payment)
            await self._uow.commit()


class RejectPayment:
    def __init__(
        self, uow: UnitOfWork, payments: PaymentRepository, obligations: ObligationRepository, clock: Clock = utc_now
    ) -> None:
        self._uow = uow
        self._payments = payments
        self._obligations = obligations
        self._clock = clock

    async def __call__(self, actor: Principal, payment_id: UUID, *, comment: str) -> None:
        actor.require(*APPROVERS)
        async with self._uow:
            payment = await _load(self._payments, payment_id)
            await _require_payment_stores(actor, APPROVERS, payment, self._obligations)
            payment.reject(by=actor.user_id, comment=comment, at=self._clock())
            await self._payments.save(payment)
            self._uow.track(payment)
            await self._uow.commit()


class CancelPayment:
    def __init__(self, uow: UnitOfWork, payments: PaymentRepository, obligations: ObligationRepository) -> None:
        self._uow = uow
        self._payments = payments
        self._obligations = obligations

    async def __call__(self, actor: Principal, payment_id: UUID) -> None:
        actor.require(*PAYERS)
        async with self._uow:
            payment = await _load(self._payments, payment_id)
            await _require_payment_stores(actor, PAYERS, payment, self._obligations)
            payment.cancel()
            await self._payments.save(payment)
            self._uow.track(payment)
            await self._uow.commit()


class PayPayment:
    """To'landi: summa nakladnoylarga taqsimlanadi. Nizo ochilgan nakladnoy — to'lab bo'lmaydi."""

    def __init__(
        self,
        uow: UnitOfWork,
        payments: PaymentRepository,
        obligations: ObligationRepository,
        attachments: Attachments,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._payments = payments
        self._obligations = obligations
        self._attachments = attachments
        self._clock = clock

    async def __call__(self, actor: Principal, payment_id: UUID, *, proof_id: UUID | None) -> None:
        actor.require(*PAYERS)
        async with self._uow:
            payment = await _load(self._payments, payment_id)
            if proof_id is not None and not await self._attachments.exists(proof_id):
                raise InvalidPaymentError("payment.proof_not_found")
            found = await self._obligations.get_many(line.obligation_id for line in payment.lines)
            _require_stores(actor, PAYERS, found.values())
            payment.pay(found, by=actor.user_id, at=self._clock(), proof_id=proof_id)
            for obligation in found.values():
                await self._obligations.save(obligation)
            await self._payments.save(payment)
            self._uow.track(payment)
            await self._uow.commit()


class ListPayments:
    def __init__(self, reader: FinanceReader, suppliers: SuppliersPort) -> None:
        self._reader = reader
        self._suppliers = suppliers

    async def __call__(
        self,
        actor: Principal,
        *,
        statuses: set[PaymentStatus] | None = None,
        supplier_id: UUID | None = None,
        limit: int = 100,
    ) -> list[PaymentListItem]:
        actor.require(*VIEWERS)
        items = await self._reader.payments(
            statuses=statuses,
            supplier_id=supplier_id,
            limit=max(1, min(limit, 200)),
            store_ids=_store_scope(actor, VIEWERS),
        )
        names, _ = await self._suppliers.labels(suppliers={i.supplier_id for i in items})
        return [replace(item, supplier_name=names.get(item.supplier_id)) for item in items]


class GetPayment:
    def __init__(self, reader: FinanceReader, suppliers: SuppliersPort) -> None:
        self._reader = reader
        self._suppliers = suppliers

    async def __call__(self, actor: Principal, payment_id: UUID) -> PaymentDetail:
        actor.require(*VIEWERS)
        detail = await self._reader.payment(payment_id, store_ids=_store_scope(actor, VIEWERS))
        if detail is None:
            raise NotFoundError("payment.not_found")
        names, _ = await self._suppliers.labels(suppliers={detail.supplier_id})
        return replace(detail, supplier_name=names.get(detail.supplier_id))


class UploadProof:
    def __init__(self, uow: UnitOfWork, attachments: Attachments, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._attachments = attachments
        self._clock = clock

    async def __call__(self, actor: Principal, *, content: bytes, content_type: str) -> UUID:
        actor.require(*PAYERS)
        if content_type not in ALLOWED_TYPES:
            raise InvalidPaymentError("payment.file_type")
        if not content or len(content) > MAX_FILE_BYTES:
            raise InvalidPaymentError("payment.file_size", max_mb=MAX_FILE_BYTES // 1024 // 1024)
        async with self._uow:
            file_id = await self._attachments.store(
                content=content, content_type=content_type, uploaded_by=actor.user_id, at=self._clock()
            )
            await self._uow.commit()
            return file_id


class GetProof:
    def __init__(self, attachments: Attachments) -> None:
        self._attachments = attachments

    async def __call__(self, actor: Principal, file_id: UUID) -> StoredFile:
        actor.require(*VIEWERS)
        stored = await self._attachments.load(file_id)
        if stored is None:
            raise NotFoundError("payment.file_not_found")
        return stored
