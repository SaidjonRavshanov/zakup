from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Table,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from zakup.platform.db import metadata

UNIT_CODES = ("kg", "g", "l", "ml", "pcs", "pack", "box", "bag")
_UNIT_CHECK = f"IN ({', '.join(repr(code) for code in UNIT_CODES)})"


def _audit_columns() -> list[Column[Any]]:
    return [
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ]


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
    Column("lead_time_days", SmallInteger, nullable=False, server_default="1"),
    Column("order_weekdays", ARRAY(SmallInteger), nullable=False, server_default="{1,2,3,4,5,6,7}"),
    Column("delivery_weekdays", ARRAY(SmallInteger), nullable=False, server_default="{1,2,3,4,5,6,7}"),
    Column("order_cutoff", Time),
    Column("contacts", JSONB, nullable=False, server_default="{}"),
    Column("payment_methods", ARRAY(Text), nullable=False, server_default="{}"),
    Column("archived_at", DateTime(timezone=True)),
    *_audit_columns(),
    CheckConstraint("payment_terms IN ('prepay', 'on_delivery', 'deferred')", name="payment_terms"),
    CheckConstraint("deferral_days BETWEEN 0 AND 120", name="deferral_days"),
    CheckConstraint("lead_time_days BETWEEN 0 AND 60", name="lead_time_days"),
    # STIR faqat faol yetkazib beruvchilar orasida unikal
    Index(
        "uq_suppliers_inn_active", "inn", unique=True, postgresql_where=text("archived_at IS NULL AND inn IS NOT NULL")
    ),
    # Qidiruv: nom bo'yicha qism-satr (ILIKE '%...%') — trigram GIN
    Index("ix_suppliers_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    schema="catalog",
)

branches = Table(
    "branches",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("iiko_id", UUID(as_uuid=True), unique=True),
    Column("code", Text),
    Column("name", Text, nullable=False),
    Column("archived_at", DateTime(timezone=True)),
    *_audit_columns(),
    schema="catalog",
)

stores = Table(
    "stores",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("iiko_id", UUID(as_uuid=True), unique=True),
    Column("branch_id", UUID(as_uuid=True), ForeignKey("catalog.branches.id")),
    Column("name", Text, nullable=False),
    Column("address", Text),
    Column("archived_at", DateTime(timezone=True)),
    *_audit_columns(),
    schema="catalog",
)

product_categories = Table(
    "product_categories",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("iiko_id", UUID(as_uuid=True), unique=True),
    Column("parent_id", UUID(as_uuid=True), ForeignKey("catalog.product_categories.id")),
    Column("name", Text, nullable=False),
    Column("monthly_budget", Numeric(18, 2)),
    *_audit_columns(),
    CheckConstraint("monthly_budget IS NULL OR monthly_budget >= 0", name="monthly_budget"),
    schema="catalog",
)

products = Table(
    "products",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("iiko_id", UUID(as_uuid=True), unique=True),
    Column("name", Text, nullable=False),
    Column("article", Text),
    Column("base_unit", Text, nullable=False),
    Column("category_id", UUID(as_uuid=True), ForeignKey("catalog.product_categories.id")),
    Column("archived_at", DateTime(timezone=True)),
    Column("synced_at", DateTime(timezone=True)),
    *_audit_columns(),
    CheckConstraint(f"base_unit {_UNIT_CHECK}", name="base_unit"),
    Index("ix_products_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    Index("ix_products_category_id", "category_id"),
    Index("ix_products_article", "article", postgresql_where=text("article IS NOT NULL")),
    schema="catalog",
)

# "Bizning tovar ↔ yetkazib beruvchi tovari" (DATABASE §2.2 supplier_products)
supplier_products = Table(
    "supplier_products",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id"), nullable=False),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), nullable=False),
    Column("supplier_sku", Text),
    Column("supplier_name", Text),
    Column("pack_unit", Text, nullable=False),
    Column("pack_factor", Numeric(18, 4), nullable=False),
    Column("order_multiple", Numeric(18, 4), nullable=False, server_default="1"),
    Column("price", Numeric(18, 4), nullable=False),
    Column("currency", Text, nullable=False, server_default="UZS"),
    Column("price_valid_from", Date, nullable=False),
    Column("archived_at", DateTime(timezone=True)),
    *_audit_columns(),
    CheckConstraint(f"pack_unit {_UNIT_CHECK}", name="pack_unit"),
    CheckConstraint("pack_factor > 0", name="pack_factor"),
    CheckConstraint("order_multiple > 0", name="order_multiple"),
    CheckConstraint("price >= 0", name="price"),
    UniqueConstraint("supplier_id", "product_id", "supplier_sku", postgresql_nulls_not_distinct=True),
    Index("ix_supplier_products_product_id", "product_id"),
    schema="catalog",
)

supplier_price_history = Table(
    "supplier_price_history",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("supplier_product_id", UUID(as_uuid=True), ForeignKey("catalog.supplier_products.id"), nullable=False),
    Column("price", Numeric(18, 4), nullable=False),
    Column("valid_from", Date, nullable=False),
    Column("source", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("source IN ('manual', 'iiko', 'supplier_response', 'receipt')", name="source"),
    Index("ix_supplier_price_history_offer", "supplier_product_id", "valid_from"),
    schema="catalog",
)

purchase_cards = Table(
    "purchase_cards",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), nullable=False),
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), nullable=False),
    Column("mode", Text, nullable=False, server_default="manual"),
    Column("safety_stock", Numeric(18, 4), nullable=False, server_default="0"),
    Column("coverage_days", SmallInteger, nullable=False, server_default="7"),
    Column("shelf_life_days", SmallInteger),
    Column("seasonal_factor", Numeric(6, 3), nullable=False, server_default="1"),
    Column("primary_supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id")),
    Column("alternative_supplier_id", UUID(as_uuid=True), ForeignKey("catalog.suppliers.id")),
    *_audit_columns(),
    UniqueConstraint("product_id", "store_id"),
    CheckConstraint("mode IN ('auto', 'manual', 'disabled')", name="mode"),
    CheckConstraint("mode <> 'auto' OR primary_supplier_id IS NOT NULL", name="auto_needs_supplier"),
    CheckConstraint("coverage_days BETWEEN 1 AND 90", name="coverage_days"),
    schema="catalog",
)
