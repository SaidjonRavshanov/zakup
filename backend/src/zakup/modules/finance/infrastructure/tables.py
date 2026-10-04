from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from zakup.platform.db import metadata

payment_number_seq = Sequence("payment_number_seq", schema="finance", metadata=metadata)

obligations = Table(
    "obligations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("receipt_id", UUID(as_uuid=True), ForeignKey("receiving.receipts.id"), nullable=False, unique=True),
    Column("receipt_number", Text, nullable=False),
    Column("supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id"), nullable=False),
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), nullable=False),
    Column("amount", Numeric(18, 2), nullable=False),
    Column("paid", Numeric(18, 2), nullable=False, server_default="0"),
    Column("received_on", Date, nullable=False),
    Column("due_date", Date, nullable=False),
    Column("status", Text, nullable=False),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'BLOCKED')", name="status"),
    CheckConstraint("amount >= 0 AND paid >= 0 AND paid <= amount", name="amounts"),
    Index(
        "ix_obligations_supplier_due",
        "supplier_id",
        "due_date",
        postgresql_where=text("status IN ('OPEN', 'PARTIALLY_PAID', 'BLOCKED')"),
    ),
    schema="finance",
)

payment_requests = Table(
    "payment_requests",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("number", Text, nullable=False, unique=True),
    Column("supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id"), nullable=False),
    Column("method", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("total", Numeric(18, 2), nullable=False),
    Column("comment", Text),
    Column("requested_by", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("approved_by", UUID(as_uuid=True), ForeignKey("identity.users.id")),
    Column("approved_at", DateTime(timezone=True)),
    Column("decision_comment", Text),
    Column("paid_by", UUID(as_uuid=True), ForeignKey("identity.users.id")),
    Column("paid_at", DateTime(timezone=True)),
    # To'lov tasdig'i — umumiy fayl omborida (receiving.attachments)
    Column("proof_id", UUID(as_uuid=True), ForeignKey("receiving.attachments.id")),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("method IN ('cash', 'transfer')", name="method"),
    CheckConstraint("status IN ('SUBMITTED', 'APPROVED', 'PAID', 'REJECTED', 'CANCELLED')", name="status"),
    Index("ix_payment_requests_supplier", "supplier_id", "requested_at"),
    schema="finance",
)

# To'lov qatori = taqsimlash (payment allocation): summa aniq nakladnoyga bog'lanadi
payment_lines = Table(
    "payment_lines",
    metadata,
    Column(
        "payment_id",
        UUID(as_uuid=True),
        ForeignKey("finance.payment_requests.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("obligation_id", UUID(as_uuid=True), ForeignKey("finance.obligations.id"), primary_key=True),
    Column("position", Integer, nullable=False),
    Column("amount", Numeric(18, 2), nullable=False),
    CheckConstraint("amount > 0", name="amount"),
    Index("ix_payment_lines_obligation", "obligation_id"),
    schema="finance",
)
