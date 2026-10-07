from typing import Any

from sqlalchemy import (
    Boolean,
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from zakup.platform.db import metadata

request_number_seq = Sequence("request_number_seq", schema="procurement", metadata=metadata)
order_number_seq = Sequence("order_number_seq", schema="procurement", metadata=metadata)

REQUEST_STATUSES = ("DRAFT", "PENDING_APPROVAL", "APPROVED", "PARTIALLY_APPROVED", "REJECTED", "CANCELLED", "SPLIT")
ORDER_STATUSES = (
    "CREATED",
    "SENT",
    "CONFIRMED",
    "PARTIALLY_CONFIRMED",
    "REAPPROVAL",
    "RECEIVED",
    "PARTIALLY_RECEIVED",
    "CANCELLED",
)


def _in(values: tuple[str, ...]) -> str:
    return f"IN ({', '.join(repr(v) for v in values)})"


def _audit() -> list[Column[Any]]:
    return [
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ]


purchase_requests = Table(
    "purchase_requests",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("number", Text, nullable=False, unique=True),
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), nullable=False),
    Column("type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("needed_by", Date, nullable=False),
    Column("initiator_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("comment", Text),
    Column("total_amount", Numeric(18, 2), nullable=False, server_default="0"),
    Column("submitted_at", DateTime(timezone=True)),
    *_audit(),
    CheckConstraint(f"status {_in(REQUEST_STATUSES)}", name="status"),
    CheckConstraint("type IN ('manual', 'event', 'auto')", name="type"),
    Index("ix_purchase_requests_store_status", "store_id", "status", "created_at"),
    Index("ix_purchase_requests_initiator", "initiator_id", "created_at"),
    schema="procurement",
)

purchase_request_lines = Table(
    "purchase_request_lines",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "request_id",
        UUID(as_uuid=True),
        ForeignKey("procurement.purchase_requests.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), nullable=False),
    Column("qty", Numeric(18, 4), nullable=False),
    Column("note", Text),
    Column("offer_id", UUID(as_uuid=True), ForeignKey("catalog.supplier_products.id")),
    Column("supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id")),
    Column("price_per_base", Numeric(18, 4)),
    # Taklif qadog'i (tanlangan paytdagi): summa buyurtmadagidek qadoqqa yaxlitlanadi
    Column("pack_unit", Text),
    Column("pack_factor", Numeric(18, 4)),
    Column("pack_multiple", Numeric(18, 4)),
    Column("price_per_pack", Numeric(18, 4)),
    Column("decision", Text, nullable=False, server_default="pending"),
    # Avto-zayavka: hisoblangan miqdor va "nega shuncha" (WORKFLOW B3)
    Column("qty_suggested", Numeric(18, 4)),
    Column("calc", JSONB),
    CheckConstraint("qty > 0", name="qty"),
    CheckConstraint("decision IN ('pending', 'approved', 'rejected')", name="decision"),
    Index("ix_purchase_request_lines_request", "request_id", "position"),
    schema="procurement",
)

approvals = Table(
    "approvals",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("request_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_requests.id"), nullable=False),
    Column("approver_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False),
    Column("decision", Text, nullable=False),
    Column("comment", Text),
    Column("amount", Numeric(18, 2), nullable=False),
    Column("role_conflict", Boolean, nullable=False, server_default="false"),
    Column("decided_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("decision IN ('approved', 'partial', 'returned', 'rejected')", name="decision"),
    Index("ix_approvals_request", "request_id", "decided_at"),
    schema="procurement",
)

purchase_orders = Table(
    "purchase_orders",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("number", Text, nullable=False, unique=True),
    Column("request_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_requests.id")),
    Column("supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id"), nullable=False),
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), nullable=False),
    Column("delivery_date", Date, nullable=False),
    Column("status", Text, nullable=False),
    Column("total_amount", Numeric(18, 2), nullable=False),
    Column("confirmed_total", Numeric(18, 2), nullable=False),
    Column("sent_at", DateTime(timezone=True)),
    Column("sent_by", UUID(as_uuid=True), ForeignKey("identity.users.id")),
    Column("sent_channel", Text),
    Column("response_deadline", DateTime(timezone=True)),
    Column("responded_at", DateTime(timezone=True)),
    Column("cancel_reason", Text),
    *_audit(),
    CheckConstraint(f"status {_in(ORDER_STATUSES)}", name="status"),
    # Faol hujjatlar ro'yxati (DATABASE §3)
    Index("ix_purchase_orders_store_status", "store_id", "status", "created_at"),
    Index("ix_purchase_orders_request", "request_id"),
    schema="procurement",
)

purchase_order_lines = Table(
    "purchase_order_lines",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "order_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_orders.id", ondelete="CASCADE"), nullable=False
    ),
    Column("position", Integer, nullable=False),
    Column("request_line_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_request_lines.id")),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), nullable=False),
    Column("offer_id", UUID(as_uuid=True), ForeignKey("catalog.supplier_products.id"), nullable=False),
    Column("pack_unit", Text, nullable=False),
    Column("pack_factor", Numeric(18, 4), nullable=False),
    Column("qty_packs", Numeric(18, 4), nullable=False),
    Column("price_per_pack", Numeric(18, 4), nullable=False),
    Column("response", Text),
    Column("qty_confirmed", Numeric(18, 4)),
    Column("price_confirmed", Numeric(18, 4)),
    Column("needs_reapproval", Boolean, nullable=False, server_default="false"),
    CheckConstraint("qty_packs > 0", name="qty_packs"),
    CheckConstraint(
        "response IS NULL OR response IN ('confirmed', 'price_changed', 'qty_changed', 'out_of_stock')", name="response"
    ),
    Index("ix_purchase_order_lines_order", "order_id", "position"),
    Index("ix_purchase_order_lines_product", "product_id"),
    schema="procurement",
)

supplier_response_tokens = Table(
    "supplier_response_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("order_id", UUID(as_uuid=True), ForeignKey("procurement.purchase_orders.id"), nullable=False),
    # Xom token saqlanmaydi — faqat SHA-256
    Column("token_hash", Text, nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="procurement",
)
