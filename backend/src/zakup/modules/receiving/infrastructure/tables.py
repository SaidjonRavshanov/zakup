from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from zakup.platform.db import metadata

receipt_number_seq = Sequence("receipt_number_seq", schema="receiving", metadata=metadata)

attachments = Table(
    "attachments",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("content_type", Text, nullable=False),
    Column("size", BigInteger, nullable=False),
    Column("sha256", Text, nullable=False),
    Column("storage_key", Text, nullable=False),
    Column("uploaded_by", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="receiving",
)

receipts = Table(
    "receipts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),  # klientda yaratiladi (oflayn, ADR-10)
    Column("number", Text, nullable=False, unique=True),
    # MVP: bitta buyurtma — bitta qabul
    Column("order_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_orders.id"), nullable=False, unique=True),
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), nullable=False),
    Column("supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id"), nullable=False),
    Column("status", Text, nullable=False),
    Column("received_by", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("supplier_invoice_no", Text),
    Column("payment_method", Text),
    Column("invoice_photo_id", UUID(as_uuid=True), ForeignKey("receiving.attachments.id"), nullable=False),
    Column("comment", Text),
    Column("total", Numeric(18, 2), nullable=False),
    Column("expected_total", Numeric(18, 2), nullable=False),
    Column("dispute_opened_at", DateTime(timezone=True)),
    Column("dispute_resolution", Text),
    Column("dispute_comment", Text),
    Column("dispute_resolved_by", UUID(as_uuid=True), ForeignKey("identity.users.id")),
    Column("dispute_resolved_at", DateTime(timezone=True)),
    # iiko kirimi holati (integration_iiko ReceiptExports facade orqali yozadi)
    Column("iiko_status", Text),
    Column("iiko_document_number", Text),
    Column("iiko_error", Text),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("status IN ('ACCEPTED', 'DISPUTED')", name="status"),
    CheckConstraint("payment_method IS NULL OR payment_method IN ('cash', 'transfer')", name="payment_method"),
    CheckConstraint(
        "dispute_resolution IS NULL OR dispute_resolution IN ('accepted', 'return', 'discount', 'replacement')",
        name="dispute_resolution",
    ),
    CheckConstraint("iiko_status IS NULL OR iiko_status IN ('pending', 'exported', 'failed')", name="iiko_status"),
    Index("ix_receipts_store_received", "store_id", "received_at"),
    schema="receiving",
)

receipt_lines = Table(
    "receipt_lines",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("receipt_id", UUID(as_uuid=True), ForeignKey("receiving.receipts.id", ondelete="CASCADE"), nullable=False),
    Column("position", Integer, nullable=False),
    Column("order_line_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_order_lines.id"), nullable=False),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), nullable=False),
    Column("base_unit", Text, nullable=False),
    Column("qty_expected", Numeric(18, 4), nullable=False),
    Column("price_expected", Numeric(18, 4), nullable=False),
    Column("qty_fact", Numeric(18, 4), nullable=False),
    Column("price_fact", Numeric(18, 4), nullable=False),
    Column("qty_defect", Numeric(18, 4), nullable=False, server_default="0"),
    Column("defect_reason", Text),
    CheckConstraint("qty_fact >= 0 AND price_fact >= 0 AND qty_defect >= 0 AND qty_defect <= qty_fact", name="amounts"),
    Index("ix_receipt_lines_receipt", "receipt_id", "position"),
    schema="receiving",
)

discrepancies = Table(
    "discrepancies",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("receipt_id", UUID(as_uuid=True), ForeignKey("receiving.receipts.id", ondelete="CASCADE"), nullable=False),
    Column("line_id", UUID(as_uuid=True), ForeignKey("receiving.receipt_lines.id", ondelete="CASCADE"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("expected", Numeric(18, 4), nullable=False),
    Column("actual", Numeric(18, 4), nullable=False),
    Column("within_tolerance", Boolean, nullable=False),
    CheckConstraint("kind IN ('qty_over', 'qty_under', 'short', 'price_up', 'price_down', 'defect')", name="kind"),
    Index("ix_discrepancies_receipt", "receipt_id"),
    schema="receiving",
)
