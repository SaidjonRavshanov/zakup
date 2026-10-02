from sqlalchemy import CheckConstraint, Column, DateTime, Index, Integer, Numeric, Table, Text, func, text
from sqlalchemy.dialects.postgresql import UUID

from zakup.platform.db import metadata

suppliers = Table(
    "suppliers",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("iiko_id", UUID(as_uuid=True), unique=True),
    Column("name", Text, nullable=False),
    Column("inn", Text),
    Column("payment_terms", Text, nullable=False),
    Column("deferral_days", Integer, nullable=False, server_default="0"),
    Column("credit_limit", Numeric(18, 2), nullable=False, server_default="0"),
    Column("min_order_amount", Numeric(18, 2), nullable=False, server_default="0"),
    Column("currency", Text, nullable=False, server_default="UZS"),
    Column("archived_at", DateTime(timezone=True)),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("payment_terms IN ('prepay', 'on_delivery', 'deferred')", name="payment_terms"),
    CheckConstraint("deferral_days BETWEEN 0 AND 120", name="deferral_days"),
    # STIR faqat faol yetkazib beruvchilar orasida unikal
    Index(
        "uq_suppliers_inn_active", "inn", unique=True, postgresql_where=text("archived_at IS NULL AND inn IS NOT NULL")
    ),
    # Qidiruv: nom bo'yicha qism-satr (ILIKE '%...%') — trigram GIN
    Index("ix_suppliers_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    schema="catalog",
)
