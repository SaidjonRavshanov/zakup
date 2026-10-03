from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from zakup.platform.db import metadata

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("telegram_id", BigInteger, nullable=False, unique=True),
    Column("full_name", Text, nullable=False),
    Column("username", Text),
    Column("locale", Text, nullable=False, server_default="uz"),
    Column("is_active", Boolean, nullable=False, server_default="false"),
    Column("activated_at", DateTime(timezone=True)),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("locale IN ('uz', 'ru')", name="locale"),
    schema="identity",
)

ROLE_CODES = ("initiator", "buyer", "approver", "storekeeper", "accountant", "auditor", "admin")

# Rol + ombor doirasi; store_id NULL — barcha omborlar (DATABASE §2.1 user_store_roles)
user_roles = Table(
    "user_roles",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False),
    Column("role", Text, nullable=False),
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("user_id", "role", "store_id", postgresql_nulls_not_distinct=True),
    CheckConstraint(f"role IN ({', '.join(repr(code) for code in ROLE_CODES)})", name="role"),
    schema="identity",
)

refresh_tokens = Table(
    "refresh_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False),
    # Xom token saqlanmaydi — faqat SHA-256 (baza sizsa ham sessiyalar o'g'irlanmaydi)
    Column("token_hash", Text, nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("ix_refresh_tokens_user_active", "user_id", postgresql_where=text("revoked_at IS NULL")),
    schema="identity",
)
