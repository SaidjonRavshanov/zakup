"""catalog: stores, products, offers (supplier_products), price history, purchase cards

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("iiko_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("monthly_budget", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "monthly_budget IS NULL OR monthly_budget >= 0", name=op.f("ck_product_categories_monthly_budget")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["catalog.product_categories.id"],
            name=op.f("fk_product_categories_parent_id_product_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_categories")),
        sa.UniqueConstraint("iiko_id", name=op.f("uq_product_categories_iiko_id")),
        schema="catalog",
    )
    op.create_table(
        "stores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("iiko_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stores")),
        sa.UniqueConstraint("iiko_id", name=op.f("uq_stores_iiko_id")),
        schema="catalog",
    )
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("iiko_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("article", sa.Text(), nullable=True),
        sa.Column("base_unit", sa.Text(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "base_unit IN ('kg', 'g', 'l', 'ml', 'pcs', 'pack', 'box', 'bag')", name=op.f("ck_products_base_unit")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["catalog.product_categories.id"], name=op.f("fk_products_category_id_product_categories")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("iiko_id", name=op.f("uq_products_iiko_id")),
        schema="catalog",
    )
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False, schema="catalog")
    op.create_index(
        "ix_products_name_trgm",
        "products",
        ["name"],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_table(
        "purchase_cards",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.Text(), server_default="manual", nullable=False),
        sa.Column("safety_stock", sa.Numeric(precision=18, scale=4), server_default="0", nullable=False),
        sa.Column("coverage_days", sa.SmallInteger(), server_default="7", nullable=False),
        sa.Column("shelf_life_days", sa.SmallInteger(), nullable=True),
        sa.Column("seasonal_factor", sa.Numeric(precision=6, scale=3), server_default="1", nullable=False),
        sa.Column("primary_supplier_id", sa.UUID(), nullable=True),
        sa.Column("alternative_supplier_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "mode <> 'auto' OR primary_supplier_id IS NOT NULL", name=op.f("ck_purchase_cards_auto_needs_supplier")
        ),
        sa.CheckConstraint("mode IN ('auto', 'manual', 'disabled')", name=op.f("ck_purchase_cards_mode")),
        sa.CheckConstraint("coverage_days BETWEEN 1 AND 90", name=op.f("ck_purchase_cards_coverage_days")),
        sa.ForeignKeyConstraint(
            ["alternative_supplier_id"],
            ["catalog.suppliers.id"],
            name=op.f("fk_purchase_cards_alternative_supplier_id_suppliers"),
        ),
        sa.ForeignKeyConstraint(
            ["primary_supplier_id"],
            ["catalog.suppliers.id"],
            name=op.f("fk_purchase_cards_primary_supplier_id_suppliers"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_purchase_cards_product_id_products")
        ),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_purchase_cards_store_id_stores")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_cards")),
        sa.UniqueConstraint("product_id", "store_id", name=op.f("uq_purchase_cards_product_id_store_id")),
        schema="catalog",
    )
    op.create_table(
        "supplier_products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("supplier_sku", sa.Text(), nullable=True),
        sa.Column("supplier_name", sa.Text(), nullable=True),
        sa.Column("pack_unit", sa.Text(), nullable=False),
        sa.Column("pack_factor", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("order_multiple", sa.Numeric(precision=18, scale=4), server_default="1", nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("currency", sa.Text(), server_default="UZS", nullable=False),
        sa.Column("price_valid_from", sa.Date(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "pack_unit IN ('kg', 'g', 'l', 'ml', 'pcs', 'pack', 'box', 'bag')",
            name=op.f("ck_supplier_products_pack_unit"),
        ),
        sa.CheckConstraint("order_multiple > 0", name=op.f("ck_supplier_products_order_multiple")),
        sa.CheckConstraint("pack_factor > 0", name=op.f("ck_supplier_products_pack_factor")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_supplier_products_price")),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_supplier_products_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["catalog.suppliers.id"], name=op.f("fk_supplier_products_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_products")),
        sa.UniqueConstraint(
            "supplier_id",
            "product_id",
            "supplier_sku",
            name=op.f("uq_supplier_products_supplier_id_product_id_supplier_sku"),
            postgresql_nulls_not_distinct=True,
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_supplier_products_product_id", "supplier_products", ["product_id"], unique=False, schema="catalog"
    )
    op.create_table(
        "supplier_price_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supplier_product_id", sa.UUID(), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "source IN ('manual', 'iiko', 'supplier_response', 'receipt')",
            name=op.f("ck_supplier_price_history_source"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_product_id"],
            ["catalog.supplier_products.id"],
            name=op.f("fk_supplier_price_history_supplier_product_id_supplier_products"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_price_history")),
        schema="catalog",
    )
    op.create_index(
        "ix_supplier_price_history_offer",
        "supplier_price_history",
        ["supplier_product_id", "valid_from"],
        unique=False,
        schema="catalog",
    )
    op.add_column(
        "suppliers",
        sa.Column("lead_time_days", sa.SmallInteger(), server_default="1", nullable=False),
        schema="catalog",
    )
    op.add_column(
        "suppliers",
        sa.Column(
            "order_weekdays", postgresql.ARRAY(sa.SmallInteger()), server_default="{1,2,3,4,5,6,7}", nullable=False
        ),
        schema="catalog",
    )
    op.add_column(
        "suppliers",
        sa.Column(
            "delivery_weekdays", postgresql.ARRAY(sa.SmallInteger()), server_default="{1,2,3,4,5,6,7}", nullable=False
        ),
        schema="catalog",
    )
    op.add_column("suppliers", sa.Column("order_cutoff", sa.Time(), nullable=True), schema="catalog")
    op.create_check_constraint(
        "ck_suppliers_lead_time_days", "suppliers", "lead_time_days BETWEEN 0 AND 60", schema="catalog"
    )
    op.add_column(
        "suppliers",
        sa.Column("contacts", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        schema="catalog",
    )
    op.create_foreign_key(
        op.f("fk_user_roles_store_id_stores"),
        "user_roles",
        "stores",
        ["store_id"],
        ["id"],
        source_schema="identity",
        referent_schema="catalog",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_user_roles_store_id_stores"), "user_roles", schema="identity", type_="foreignkey")
    op.drop_constraint("ck_suppliers_lead_time_days", "suppliers", schema="catalog", type_="check")
    op.drop_column("suppliers", "contacts", schema="catalog")
    op.drop_column("suppliers", "order_cutoff", schema="catalog")
    op.drop_column("suppliers", "delivery_weekdays", schema="catalog")
    op.drop_column("suppliers", "order_weekdays", schema="catalog")
    op.drop_column("suppliers", "lead_time_days", schema="catalog")
    op.drop_index("ix_supplier_price_history_offer", table_name="supplier_price_history", schema="catalog")
    op.drop_table("supplier_price_history", schema="catalog")
    op.drop_index("ix_supplier_products_product_id", table_name="supplier_products", schema="catalog")
    op.drop_table("supplier_products", schema="catalog")
    op.drop_table("purchase_cards", schema="catalog")
    op.drop_index(
        "ix_products_name_trgm",
        table_name="products",
        schema="catalog",
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.drop_index("ix_products_category_id", table_name="products", schema="catalog")
    op.drop_table("products", schema="catalog")
    op.drop_table("stores", schema="catalog")
    op.drop_table("product_categories", schema="catalog")
