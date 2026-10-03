"""iiko: links, sync_runs; catalog: branches, stores.branch_id, suppliers.payment_methods

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("iiko_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branches")),
        sa.UniqueConstraint("iiko_id", name=op.f("uq_branches_iiko_id")),
        schema="catalog",
    )
    op.create_table(
        "links",
        sa.Column("server_code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("iiko_id", sa.UUID(), nullable=False),
        sa.Column("local_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.Text(), nullable=True),
        sa.Column("attrs", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('branch', 'store', 'category', 'product', 'supplier')", name=op.f("ck_links_kind")
        ),
        sa.PrimaryKeyConstraint("server_code", "kind", "iiko_id", name=op.f("pk_links")),
        schema="iiko",
    )
    op.create_index("ix_links_kind_iiko_id", "links", ["kind", "iiko_id"], unique=False, schema="iiko")
    op.create_index(
        "ix_links_kind_key",
        "links",
        ["kind", "key"],
        unique=False,
        schema="iiko",
        postgresql_where=sa.text("key IS NOT NULL"),
    )
    op.create_index("ix_links_kind_local_id", "links", ["kind", "local_id"], unique=False, schema="iiko")
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("server_code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('references', 'purchase_prices')", name=op.f("ck_sync_runs_kind")),
        sa.CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name=op.f("ck_sync_runs_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
        schema="iiko",
    )
    op.create_index(
        "ix_sync_runs_queued",
        "sync_runs",
        ["created_at"],
        unique=False,
        schema="iiko",
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "ix_sync_runs_server_created", "sync_runs", ["server_code", "created_at"], unique=False, schema="iiko"
    )
    op.create_index(
        "ix_products_article",
        "products",
        ["article"],
        unique=False,
        schema="catalog",
        postgresql_where=sa.text("article IS NOT NULL"),
    )
    op.add_column("stores", sa.Column("branch_id", sa.UUID(), nullable=True), schema="catalog")
    op.create_foreign_key(
        op.f("fk_stores_branch_id_branches"),
        "stores",
        "branches",
        ["branch_id"],
        ["id"],
        source_schema="catalog",
        referent_schema="catalog",
    )
    op.add_column(
        "suppliers",
        sa.Column("payment_methods", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        schema="catalog",
    )


def downgrade() -> None:
    op.drop_column("suppliers", "payment_methods", schema="catalog")
    op.drop_constraint(op.f("fk_stores_branch_id_branches"), "stores", schema="catalog", type_="foreignkey")
    op.drop_column("stores", "branch_id", schema="catalog")
    op.drop_index(
        "ix_products_article", table_name="products", schema="catalog", postgresql_where=sa.text("article IS NOT NULL")
    )
    op.drop_index("ix_sync_runs_server_created", table_name="sync_runs", schema="iiko")
    op.drop_index(
        "ix_sync_runs_queued", table_name="sync_runs", schema="iiko", postgresql_where=sa.text("status = 'queued'")
    )
    op.drop_table("sync_runs", schema="iiko")
    op.drop_index("ix_links_kind_local_id", table_name="links", schema="iiko")
    op.drop_index("ix_links_kind_key", table_name="links", schema="iiko", postgresql_where=sa.text("key IS NOT NULL"))
    op.drop_index("ix_links_kind_iiko_id", table_name="links", schema="iiko")
    op.drop_table("links", schema="iiko")
    op.drop_table("branches", schema="catalog")
