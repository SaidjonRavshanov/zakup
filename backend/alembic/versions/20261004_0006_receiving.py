"""receiving: qabul, qatorlar, farqlar, fayllar; iiko.invoice_exports; PO holatlari RECEIVED / PARTIALLY_RECEIVED

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ORDER_STATUSES = "'CREATED', 'SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED', 'REAPPROVAL', 'CANCELLED'"
NEW_ORDER_STATUSES = OLD_ORDER_STATUSES + ", 'RECEIVED', 'PARTIALLY_RECEIVED'"


def _order_status_check(values: str) -> None:
    op.drop_constraint(op.f("ck_purchase_orders_status"), "purchase_orders", schema="procurement", type_="check")
    op.create_check_constraint(
        op.f("ck_purchase_orders_status"), "purchase_orders", f"status IN ({values})", schema="procurement"
    )


def upgrade() -> None:
    op.execute("CREATE SEQUENCE receiving.receipt_number_seq")
    _order_status_check(NEW_ORDER_STATUSES)
    op.create_table(
        "invoice_exports",
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("document_number", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name=op.f("ck_invoice_exports_status")),
        sa.PrimaryKeyConstraint("receipt_id", name=op.f("pk_invoice_exports")),
        schema="iiko",
    )
    op.create_index(
        "ix_invoice_exports_due",
        "invoice_exports",
        ["next_attempt_at"],
        unique=False,
        schema="iiko",
        postgresql_where=sa.text("status IN ('queued', 'failed')"),
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("uploaded_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["identity.users.id"], name=op.f("fk_attachments_uploaded_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        schema="receiving",
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("received_by", sa.UUID(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_invoice_no", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.Text(), nullable=True),
        sa.Column("invoice_photo_id", sa.UUID(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("expected_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("dispute_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispute_resolution", sa.Text(), nullable=True),
        sa.Column("dispute_comment", sa.Text(), nullable=True),
        sa.Column("dispute_resolved_by", sa.UUID(), nullable=True),
        sa.Column("dispute_resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("iiko_status", sa.Text(), nullable=True),
        sa.Column("iiko_document_number", sa.Text(), nullable=True),
        sa.Column("iiko_error", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "dispute_resolution IS NULL OR dispute_resolution IN ('accepted', 'return', 'discount', 'replacement')",
            name=op.f("ck_receipts_dispute_resolution"),
        ),
        sa.CheckConstraint(
            "iiko_status IS NULL OR iiko_status IN ('pending', 'exported', 'failed')",
            name=op.f("ck_receipts_iiko_status"),
        ),
        sa.CheckConstraint(
            "payment_method IS NULL OR payment_method IN ('cash', 'transfer')", name=op.f("ck_receipts_payment_method")
        ),
        sa.CheckConstraint("status IN ('ACCEPTED', 'DISPUTED')", name=op.f("ck_receipts_status")),
        sa.ForeignKeyConstraint(
            ["dispute_resolved_by"], ["identity.users.id"], name=op.f("fk_receipts_dispute_resolved_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["invoice_photo_id"], ["receiving.attachments.id"], name=op.f("fk_receipts_invoice_photo_id_attachments")
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["procurement.purchase_orders.id"], name=op.f("fk_receipts_order_id_purchase_orders")
        ),
        sa.ForeignKeyConstraint(["received_by"], ["identity.users.id"], name=op.f("fk_receipts_received_by_users")),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_receipts_store_id_stores")),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["catalog.suppliers.id"], name=op.f("fk_receipts_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipts")),
        sa.UniqueConstraint("number", name=op.f("uq_receipts_number")),
        sa.UniqueConstraint("order_id", name=op.f("uq_receipts_order_id")),
        schema="receiving",
    )
    op.create_index(
        "ix_receipts_store_received", "receipts", ["store_id", "received_at"], unique=False, schema="receiving"
    )
    op.create_table(
        "receipt_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("order_line_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("base_unit", sa.Text(), nullable=False),
        sa.Column("qty_expected", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("price_expected", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("qty_fact", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("price_fact", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("qty_defect", sa.Numeric(precision=18, scale=4), server_default="0", nullable=False),
        sa.Column("defect_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "qty_fact >= 0 AND price_fact >= 0 AND qty_defect >= 0 AND qty_defect <= qty_fact",
            name=op.f("ck_receipt_lines_amounts"),
        ),
        sa.ForeignKeyConstraint(
            ["order_line_id"],
            ["procurement.purchase_order_lines.id"],
            name=op.f("fk_receipt_lines_order_line_id_purchase_order_lines"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_receipt_lines_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receiving.receipts.id"],
            name=op.f("fk_receipt_lines_receipt_id_receipts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipt_lines")),
        schema="receiving",
    )
    op.create_index(
        "ix_receipt_lines_receipt", "receipt_lines", ["receipt_id", "position"], unique=False, schema="receiving"
    )
    op.create_table(
        "discrepancies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("line_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("expected", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("actual", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("within_tolerance", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('qty_over', 'qty_under', 'short', 'price_up', 'price_down', 'defect')",
            name=op.f("ck_discrepancies_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["line_id"],
            ["receiving.receipt_lines.id"],
            name=op.f("fk_discrepancies_line_id_receipt_lines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receiving.receipts.id"],
            name=op.f("fk_discrepancies_receipt_id_receipts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_discrepancies")),
        schema="receiving",
    )
    op.create_index("ix_discrepancies_receipt", "discrepancies", ["receipt_id"], unique=False, schema="receiving")


def downgrade() -> None:
    op.drop_index("ix_discrepancies_receipt", table_name="discrepancies", schema="receiving")
    op.drop_table("discrepancies", schema="receiving")
    op.drop_index("ix_receipt_lines_receipt", table_name="receipt_lines", schema="receiving")
    op.drop_table("receipt_lines", schema="receiving")
    op.drop_index("ix_receipts_store_received", table_name="receipts", schema="receiving")
    op.drop_table("receipts", schema="receiving")
    op.drop_table("attachments", schema="receiving")
    op.drop_index(
        "ix_invoice_exports_due",
        table_name="invoice_exports",
        schema="iiko",
        postgresql_where=sa.text("status IN ('queued', 'failed')"),
    )
    op.drop_table("invoice_exports", schema="iiko")
    _order_status_check(OLD_ORDER_STATUSES)
    op.execute("DROP SEQUENCE receiving.receipt_number_seq")
