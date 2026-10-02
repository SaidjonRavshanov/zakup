"""init: modul sxemalari, platform.outbox, catalog.suppliers

Revision ID: 0001
Revises:
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = (
    "identity",
    "catalog",
    "planning",
    "procurement",
    "receiving",
    "finance",
    "iiko",
    "notify",
    "audit",
    "platform",
)


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "outbox",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_type", sa.Text, nullable=False),
        sa.Column("aggregate_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_error", sa.Text),
        sa.PrimaryKeyConstraint("id", name="pk_outbox"),
        schema="platform",
    )
    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["next_attempt_at"],
        schema="platform",
        postgresql_where=sa.text("processed_at IS NULL"),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("iiko_id", pg.UUID(as_uuid=True)),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("inn", sa.Text),
        sa.Column("payment_terms", sa.Text, nullable=False),
        sa.Column("deferral_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credit_limit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("min_order_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.Text, nullable=False, server_default="UZS"),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
        sa.UniqueConstraint("iiko_id", name="uq_suppliers_iiko_id"),
        sa.CheckConstraint("payment_terms IN ('prepay', 'on_delivery', 'deferred')", name="ck_suppliers_payment_terms"),
        sa.CheckConstraint("deferral_days BETWEEN 0 AND 120", name="ck_suppliers_deferral_days"),
        schema="catalog",
    )
    op.create_index(
        "uq_suppliers_inn_active",
        "suppliers",
        ["inn"],
        unique=True,
        schema="catalog",
        postgresql_where=sa.text("archived_at IS NULL AND inn IS NOT NULL"),
    )
    op.execute("CREATE INDEX ix_suppliers_name_trgm ON catalog.suppliers USING gin (name gin_trgm_ops)")


def downgrade() -> None:
    op.drop_table("suppliers", schema="catalog")
    op.drop_table("outbox", schema="platform")
    for schema in reversed(SCHEMAS):
        if schema != "platform":  # alembic_version shu yerda
            op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
