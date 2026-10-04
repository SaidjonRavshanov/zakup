"""finance: majburiyatlar (nakladnoy bo'yicha qarz), to'lov zayavkalari va taqsimlash

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE finance.payment_number_seq")
    op.create_table(
        "payment_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("paid_by", sa.UUID(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proof_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("method IN ('cash', 'transfer')", name=op.f("ck_payment_requests_method")),
        sa.CheckConstraint(
            "status IN ('SUBMITTED', 'APPROVED', 'PAID', 'REJECTED', 'CANCELLED')",
            name=op.f("ck_payment_requests_status"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["identity.users.id"], name=op.f("fk_payment_requests_approved_by_users")
        ),
        sa.ForeignKeyConstraint(["paid_by"], ["identity.users.id"], name=op.f("fk_payment_requests_paid_by_users")),
        sa.ForeignKeyConstraint(
            ["proof_id"], ["receiving.attachments.id"], name=op.f("fk_payment_requests_proof_id_attachments")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["identity.users.id"], name=op.f("fk_payment_requests_requested_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["catalog.suppliers.id"], name=op.f("fk_payment_requests_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_requests")),
        sa.UniqueConstraint("number", name=op.f("uq_payment_requests_number")),
        schema="finance",
    )
    op.create_index(
        "ix_payment_requests_supplier",
        "payment_requests",
        ["supplier_id", "requested_at"],
        unique=False,
        schema="finance",
    )
    op.create_table(
        "obligations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("receipt_number", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("paid", sa.Numeric(precision=18, scale=2), server_default="0", nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'BLOCKED')", name=op.f("ck_obligations_status")
        ),
        sa.CheckConstraint("amount >= 0 AND paid >= 0 AND paid <= amount", name=op.f("ck_obligations_amounts")),
        sa.ForeignKeyConstraint(
            ["receipt_id"], ["receiving.receipts.id"], name=op.f("fk_obligations_receipt_id_receipts")
        ),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_obligations_store_id_stores")),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["catalog.suppliers.id"], name=op.f("fk_obligations_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_obligations")),
        sa.UniqueConstraint("receipt_id", name=op.f("uq_obligations_receipt_id")),
        schema="finance",
    )
    op.create_index(
        "ix_obligations_supplier_due",
        "obligations",
        ["supplier_id", "due_date"],
        unique=False,
        schema="finance",
        postgresql_where=sa.text("status IN ('OPEN', 'PARTIALLY_PAID', 'BLOCKED')"),
    )
    op.create_table(
        "payment_lines",
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("obligation_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_payment_lines_amount")),
        sa.ForeignKeyConstraint(
            ["obligation_id"], ["finance.obligations.id"], name=op.f("fk_payment_lines_obligation_id_obligations")
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["finance.payment_requests.id"],
            name=op.f("fk_payment_lines_payment_id_payment_requests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("payment_id", "obligation_id", name=op.f("pk_payment_lines")),
        schema="finance",
    )
    op.create_index("ix_payment_lines_obligation", "payment_lines", ["obligation_id"], unique=False, schema="finance")


def downgrade() -> None:
    op.drop_index("ix_payment_lines_obligation", table_name="payment_lines", schema="finance")
    op.drop_table("payment_lines", schema="finance")
    op.drop_index(
        "ix_obligations_supplier_due",
        table_name="obligations",
        schema="finance",
        postgresql_where=sa.text("status IN ('OPEN', 'PARTIALLY_PAID', 'BLOCKED')"),
    )
    op.drop_table("obligations", schema="finance")
    op.drop_index("ix_payment_requests_supplier", table_name="payment_requests", schema="finance")
    op.drop_table("payment_requests", schema="finance")
    op.execute("DROP SEQUENCE finance.payment_number_seq")
