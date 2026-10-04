"""procurement: zayavkalar, tasdiqlashlar, buyurtmalar (PO), yetkazuvchi javob tokenlari

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE procurement.request_number_seq")
    op.execute("CREATE SEQUENCE procurement.order_number_seq")
    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("needed_by", sa.Date(), nullable=False),
        sa.Column("initiator_id", sa.UUID(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), server_default="0", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'PARTIALLY_APPROVED',"
            " 'REJECTED', 'CANCELLED', 'SPLIT')",
            name=op.f("ck_purchase_requests_status"),
        ),
        sa.CheckConstraint("type IN ('manual', 'event', 'auto')", name=op.f("ck_purchase_requests_type")),
        sa.ForeignKeyConstraint(
            ["initiator_id"], ["identity.users.id"], name=op.f("fk_purchase_requests_initiator_id_users")
        ),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_purchase_requests_store_id_stores")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_requests")),
        sa.UniqueConstraint("number", name=op.f("uq_purchase_requests_number")),
        schema="procurement",
    )
    op.create_index(
        "ix_purchase_requests_initiator",
        "purchase_requests",
        ["initiator_id", "created_at"],
        unique=False,
        schema="procurement",
    )
    op.create_index(
        "ix_purchase_requests_store_status",
        "purchase_requests",
        ["store_id", "status", "created_at"],
        unique=False,
        schema="procurement",
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("approver_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("role_conflict", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'partial', 'returned', 'rejected')", name=op.f("ck_approvals_decision")
        ),
        sa.ForeignKeyConstraint(["approver_id"], ["identity.users.id"], name=op.f("fk_approvals_approver_id_users")),
        sa.ForeignKeyConstraint(
            ["request_id"], ["procurement.purchase_requests.id"], name=op.f("fk_approvals_request_id_purchase_requests")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
        schema="procurement",
    )
    op.create_index(
        "ix_approvals_request", "approvals", ["request_id", "decided_at"], unique=False, schema="procurement"
    )
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("confirmed_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_by", sa.UUID(), nullable=True),
        sa.Column("sent_channel", sa.Text(), nullable=True),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('CREATED', 'SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED', 'REAPPROVAL', 'CANCELLED')",
            name=op.f("ck_purchase_orders_status"),
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement.purchase_requests.id"],
            name=op.f("fk_purchase_orders_request_id_purchase_requests"),
        ),
        sa.ForeignKeyConstraint(["sent_by"], ["identity.users.id"], name=op.f("fk_purchase_orders_sent_by_users")),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_purchase_orders_store_id_stores")),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["catalog.suppliers.id"], name=op.f("fk_purchase_orders_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_orders")),
        sa.UniqueConstraint("number", name=op.f("uq_purchase_orders_number")),
        schema="procurement",
    )
    op.create_index("ix_purchase_orders_request", "purchase_orders", ["request_id"], unique=False, schema="procurement")
    op.create_index(
        "ix_purchase_orders_store_status",
        "purchase_orders",
        ["store_id", "status", "created_at"],
        unique=False,
        schema="procurement",
    )
    op.create_table(
        "purchase_request_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("qty", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("offer_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("price_per_base", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("decision", sa.Text(), server_default="pending", nullable=False),
        sa.CheckConstraint(
            "decision IN ('pending', 'approved', 'rejected')", name=op.f("ck_purchase_request_lines_decision")
        ),
        sa.CheckConstraint("qty > 0", name=op.f("ck_purchase_request_lines_qty")),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["catalog.supplier_products.id"],
            name=op.f("fk_purchase_request_lines_offer_id_supplier_products"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_purchase_request_lines_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement.purchase_requests.id"],
            name=op.f("fk_purchase_request_lines_request_id_purchase_requests"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["catalog.suppliers.id"], name=op.f("fk_purchase_request_lines_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_request_lines")),
        schema="procurement",
    )
    op.create_index(
        "ix_purchase_request_lines_request",
        "purchase_request_lines",
        ["request_id", "position"],
        unique=False,
        schema="procurement",
    )
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("request_line_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("offer_id", sa.UUID(), nullable=False),
        sa.Column("pack_unit", sa.Text(), nullable=False),
        sa.Column("pack_factor", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("qty_packs", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("price_per_pack", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("qty_confirmed", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("price_confirmed", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("needs_reapproval", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint(
            "response IS NULL OR response IN ('confirmed', 'price_changed', 'qty_changed', 'out_of_stock')",
            name=op.f("ck_purchase_order_lines_response"),
        ),
        sa.CheckConstraint("qty_packs > 0", name=op.f("ck_purchase_order_lines_qty_packs")),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["catalog.supplier_products.id"],
            name=op.f("fk_purchase_order_lines_offer_id_supplier_products"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["procurement.purchase_orders.id"],
            name=op.f("fk_purchase_order_lines_order_id_purchase_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_purchase_order_lines_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["request_line_id"],
            ["procurement.purchase_request_lines.id"],
            name=op.f("fk_purchase_order_lines_request_line_id_purchase_request_lines"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order_lines")),
        schema="procurement",
    )
    op.create_index(
        "ix_purchase_order_lines_order",
        "purchase_order_lines",
        ["order_id", "position"],
        unique=False,
        schema="procurement",
    )
    op.create_index(
        "ix_purchase_order_lines_product", "purchase_order_lines", ["product_id"], unique=False, schema="procurement"
    )
    op.create_table(
        "supplier_response_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["procurement.purchase_orders.id"],
            name=op.f("fk_supplier_response_tokens_order_id_purchase_orders"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_response_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_supplier_response_tokens_token_hash")),
        schema="procurement",
    )


def downgrade() -> None:
    op.drop_table("supplier_response_tokens", schema="procurement")
    op.drop_index("ix_purchase_order_lines_product", table_name="purchase_order_lines", schema="procurement")
    op.drop_index("ix_purchase_order_lines_order", table_name="purchase_order_lines", schema="procurement")
    op.drop_table("purchase_order_lines", schema="procurement")
    op.drop_index("ix_purchase_request_lines_request", table_name="purchase_request_lines", schema="procurement")
    op.drop_table("purchase_request_lines", schema="procurement")
    op.drop_index("ix_purchase_orders_store_status", table_name="purchase_orders", schema="procurement")
    op.drop_index("ix_purchase_orders_request", table_name="purchase_orders", schema="procurement")
    op.drop_table("purchase_orders", schema="procurement")
    op.drop_index("ix_approvals_request", table_name="approvals", schema="procurement")
    op.drop_table("approvals", schema="procurement")
    op.drop_index("ix_purchase_requests_store_status", table_name="purchase_requests", schema="procurement")
    op.drop_index("ix_purchase_requests_initiator", table_name="purchase_requests", schema="procurement")
    op.drop_table("purchase_requests", schema="procurement")
    op.execute("DROP SEQUENCE procurement.order_number_seq")
    op.execute("DROP SEQUENCE procurement.request_number_seq")
