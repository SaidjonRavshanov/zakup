"""Qabul use case'lari (WORKFLOW B8, B9). Ruxsat — ombor doirasida (ARCHITECTURE §7)."""

from dataclasses import replace
from uuid import UUID

from zakup.modules.receiving.application.dto import ReceiptDetail, ReceiptListItem, SubmitReceiptCommand
from zakup.modules.receiving.application.ports import (
    Attachments,
    ExpectedOrder,
    LabelsPort,
    OrdersPort,
    ReceiptReader,
    ReceiptRepository,
    StoredFile,
)
from zakup.modules.receiving.domain.receipt import (
    ExpectedLine,
    FactLine,
    InvalidReceiptError,
    Receipt,
    ReceiptHeader,
    ReceiptStatus,
    ReceivingTolerance,
    Resolution,
)
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.errors import ConflictError, NotFoundError
from zakup.shared_kernel.ids import new_id
from zakup.shared_kernel.uow import UnitOfWork

RECEIVERS = (Role.STOREKEEPER, Role.BUYER, Role.ADMIN)
DECIDERS = (Role.APPROVER, Role.BUYER, Role.ADMIN)
VIEWERS = (Role.STOREKEEPER, Role.BUYER, Role.APPROVER, Role.ADMIN, Role.AUDITOR, Role.ACCOUNTANT)
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "application/pdf"})


class SubmitReceipt:
    """Oflayn yig'ilgan qabul — bitta so'rovda. Bir xil ID bilan qayta yuborish — xavfsiz (natija qaytadi)."""

    def __init__(
        self,
        uow: UnitOfWork,
        receipts: ReceiptRepository,
        orders: OrdersPort,
        attachments: Attachments,
        *,
        tolerance: ReceivingTolerance,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._receipts = receipts
        self._orders = orders
        self._attachments = attachments
        self._tolerance = tolerance
        self._clock = clock

    async def __call__(self, actor: Principal, cmd: SubmitReceiptCommand) -> ReceiptStatus:
        async with self._uow:
            existing = await self._receipts.get(cmd.id)
            if existing is not None:
                if existing.header.order_id != cmd.order_id:
                    raise ConflictError("receipt.id_reused")
                return existing.status  # takroriy yuborish (oflayn navbat)
            if await self._receipts.find_by_order(cmd.order_id) is not None:
                raise ConflictError("receipt.order_already_received")
            order = await self._orders.expected(cmd.order_id)
            actor.require(*RECEIVERS, store_id=order.store_id)
            if not await self._attachments.exists(cmd.invoice_photo_id):
                raise InvalidReceiptError("receipt.photo_required")

            receipt = Receipt.submit(
                id=cmd.id,
                number=await self._receipts.next_number(),
                header=ReceiptHeader(
                    order_id=order.order_id,
                    store_id=order.store_id,
                    supplier_id=order.supplier_id,
                    received_by=actor.user_id,
                    received_at=self._clock(),
                    supplier_invoice_no=cmd.supplier_invoice_no,
                    payment_method=cmd.payment_method,
                    invoice_photo_id=cmd.invoice_photo_id,
                    comment=cmd.comment,
                ),
                expected=[
                    ExpectedLine(line.order_line_id, line.product_id, line.base_unit, line.qty, line.price)
                    for line in order.lines
                ],
                facts=[FactLine(f.order_line_id, f.qty, f.price, f.qty_defect, f.defect_reason) for f in cmd.lines],
                line_ids=[new_id() for _ in order.lines],
                tolerance=self._tolerance,
            )
            await self._receipts.add(receipt)
            await self._orders.mark_received(order.order_id, complete=receipt.is_complete)
            self._uow.track(receipt)
            await self._uow.commit()
            return receipt.status


class ResolveDispute:
    def __init__(self, uow: UnitOfWork, receipts: ReceiptRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._receipts = receipts
        self._clock = clock

    async def __call__(self, actor: Principal, receipt_id: UUID, *, resolution: Resolution, comment: str) -> None:
        async with self._uow:
            receipt = await self._receipts.get(receipt_id)
            if receipt is None:
                raise NotFoundError("receipt.not_found")
            actor.require(*DECIDERS, store_id=receipt.header.store_id)
            receipt.resolve_dispute(by=actor.user_id, resolution=resolution, comment=comment, at=self._clock())
            await self._receipts.save(receipt)
            self._uow.track(receipt)
            await self._uow.commit()


class UploadAttachment:
    def __init__(self, uow: UnitOfWork, attachments: Attachments, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._attachments = attachments
        self._clock = clock

    async def __call__(self, actor: Principal, *, content: bytes, content_type: str) -> UUID:
        actor.require(*RECEIVERS)
        if content_type not in ALLOWED_TYPES:
            raise InvalidReceiptError("receipt.file_type")
        if not content or len(content) > MAX_FILE_BYTES:
            raise InvalidReceiptError("receipt.file_size", max_mb=MAX_FILE_BYTES // 1024 // 1024)
        async with self._uow:
            file_id = await self._attachments.store(
                content=content, content_type=content_type, uploaded_by=actor.user_id, at=self._clock()
            )
            await self._uow.commit()
            return file_id


class GetAttachment:
    def __init__(self, attachments: Attachments) -> None:
        self._attachments = attachments

    async def __call__(self, actor: Principal, file_id: UUID) -> StoredFile:
        actor.require(*VIEWERS)
        stored = await self._attachments.load(file_id)
        if stored is None:
            raise NotFoundError("receipt.file_not_found")
        return stored


class ListReceipts:
    def __init__(self, reader: ReceiptReader, labels: LabelsPort) -> None:
        self._reader = reader
        self._labels = labels

    async def __call__(
        self, actor: Principal, *, statuses: set[ReceiptStatus] | None = None, limit: int = 100
    ) -> list[ReceiptListItem]:
        actor.require(*VIEWERS)
        grants = [g for g in actor.grants if g.role in VIEWERS]
        stores = None if any(g.store_id is None for g in grants) else {g.store_id for g in grants if g.store_id}
        items = await self._reader.list(store_ids=stores, statuses=statuses, limit=max(1, min(limit, 200)))
        _, suppliers, store_names = await self._labels.labels(
            suppliers={i.supplier_id for i in items}, stores={i.store_id for i in items}
        )
        return [
            replace(item, supplier_name=suppliers.get(item.supplier_id), store_name=store_names.get(item.store_id))
            for item in items
        ]


class GetReceipt:
    def __init__(self, reader: ReceiptReader, labels: LabelsPort) -> None:
        self._reader = reader
        self._labels = labels

    async def __call__(self, actor: Principal, receipt_id: UUID) -> ReceiptDetail:
        detail = await self._reader.detail(receipt_id)
        if detail is None:
            raise NotFoundError("receipt.not_found")
        actor.require(*VIEWERS, store_id=detail.store_id)
        products, suppliers, stores = await self._labels.labels(
            products={line.product_id for line in detail.lines},
            suppliers={detail.supplier_id},
            stores={detail.store_id},
        )
        return replace(
            detail,
            lines=tuple(replace(line, product_name=products.get(line.product_id, "?")) for line in detail.lines),
            supplier_name=suppliers.get(detail.supplier_id),
            store_name=stores.get(detail.store_id),
        )


class GetOrderToReceive:
    """Qabul ekrani uchun: kutilgan pozitsiyalar (bazaviy birlikda, tasdiqlangan narx bilan)."""

    def __init__(self, orders: OrdersPort) -> None:
        self._orders = orders

    async def __call__(self, actor: Principal, order_id: UUID) -> ExpectedOrder:
        order = await self._orders.expected(order_id)
        actor.require(*RECEIVERS, store_id=order.store_id)
        return order
