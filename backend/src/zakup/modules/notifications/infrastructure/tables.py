from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
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

# Bot xabarlari navbati: (key, user_id) — idempotent (event qayta ishlansa ham xabar bitta)
messages = Table(
    "messages",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("key", UUID(as_uuid=True), nullable=False),
    Column("user_id", UUID(as_uuid=True), nullable=False),
    Column("chat_id", BigInteger, nullable=False),
    Column("locale", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("path", Text),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("next_attempt_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("last_error", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("sent_at", DateTime(timezone=True)),
    UniqueConstraint("key", "user_id"),
    CheckConstraint("status IN ('pending', 'sent', 'failed')", name="status"),
    Index("ix_messages_pending", "next_attempt_at", postgresql_where=text("status = 'pending'")),
    schema="notify",
)
