"""identity: users, user_roles, refresh_tokens

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_CODES = ("initiator", "buyer", "approver", "storekeeper", "accountant", "auditor", "admin")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_id", sa.BigInteger, nullable=False),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("username", sa.Text),
        sa.Column("locale", sa.Text, nullable=False, server_default="uz"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
        sa.CheckConstraint("locale IN ('uz', 'ru')", name="ck_users_locale"),
        schema="identity",
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("store_id", pg.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity.users.id"], name="fk_user_roles_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "user_id",
            "role",
            "store_id",
            name="uq_user_roles_user_id_role_store_id",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(f"role IN ({', '.join(repr(code) for code in ROLE_CODES)})", name="ck_user_roles_role"),
        schema="identity",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity.users.id"], name="fk_refresh_tokens_user_id_users", ondelete="CASCADE"
        ),
        schema="identity",
    )
    op.create_index(
        "ix_refresh_tokens_user_active",
        "refresh_tokens",
        ["user_id"],
        schema="identity",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens", schema="identity")
    op.drop_table("user_roles", schema="identity")
    op.drop_table("users", schema="identity")
