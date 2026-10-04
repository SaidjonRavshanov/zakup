"""planning: qoldiq va kunlik sarf (iiko); avto-zayavka: qatorda hisob ("nega shuncha"); kunlik ishlar;
tizim foydalanuvchisi (avtomatik hujjatlar muallifi)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_USER_ID = "00000000-0000-7000-8000-000000000001"
OLD_SYNC_KINDS = "'references', 'purchase_prices'"
NEW_SYNC_KINDS = OLD_SYNC_KINDS + ", 'stock', 'consumption'"


def _sync_kind_check(values: str) -> None:
    op.drop_constraint(op.f("ck_sync_runs_kind"), "sync_runs", schema="iiko", type_="check")
    op.create_check_constraint(op.f("ck_sync_runs_kind"), "sync_runs", f"kind IN ({values})", schema="iiko")


def upgrade() -> None:
    _sync_kind_check(NEW_SYNC_KINDS)
    op.create_table(
        "daily_jobs",
        sa.Column("job", sa.Text(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("ran_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("job", "day", name=op.f("pk_daily_jobs")),
        schema="platform",
    )
    op.create_table(
        "consumption_daily",
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("qty", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_consumption_daily_product_id_products")
        ),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_consumption_daily_store_id_stores")),
        sa.PrimaryKeyConstraint("store_id", "product_id", "day", name=op.f("pk_consumption_daily")),
        schema="planning",
    )
    op.create_index(
        "ix_consumption_daily_store_day", "consumption_daily", ["store_id", "day"], unique=False, schema="planning"
    )
    op.create_table(
        "stock_current",
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("qty", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog.products.id"], name=op.f("fk_stock_current_product_id_products")
        ),
        sa.ForeignKeyConstraint(["store_id"], ["catalog.stores.id"], name=op.f("fk_stock_current_store_id_stores")),
        sa.PrimaryKeyConstraint("store_id", "product_id", name=op.f("pk_stock_current")),
        schema="planning",
    )
    op.add_column(
        "purchase_request_lines",
        sa.Column("qty_suggested", sa.Numeric(precision=18, scale=4), nullable=True),
        schema="procurement",
    )
    op.add_column(
        "purchase_request_lines",
        sa.Column("calc", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="procurement",
    )

    # Faol emas: tizimga kira olmaydi, faqat avtomatik hujjatlar muallifi sifatida ko'rinadi
    op.execute(
        "INSERT INTO identity.users (id, telegram_id, full_name, locale, is_active)"  # noqa: S608 — konstanta
        f" VALUES ('{SYSTEM_USER_ID}', 0, 'Tizim', 'uz', false) ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM iiko.sync_runs WHERE kind IN ('stock', 'consumption')")
    _sync_kind_check(OLD_SYNC_KINDS)
    op.execute(f"DELETE FROM identity.users WHERE id = '{SYSTEM_USER_ID}'")  # noqa: S608 — konstanta
    op.drop_column("purchase_request_lines", "calc", schema="procurement")
    op.drop_column("purchase_request_lines", "qty_suggested", schema="procurement")
    op.drop_table("stock_current", schema="planning")
    op.drop_index("ix_consumption_daily_store_day", table_name="consumption_daily", schema="planning")
    op.drop_table("consumption_daily", schema="planning")
    op.drop_table("daily_jobs", schema="platform")
