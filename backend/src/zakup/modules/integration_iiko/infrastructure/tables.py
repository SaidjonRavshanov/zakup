from sqlalchemy import CheckConstraint, Column, DateTime, Index, PrimaryKeyConstraint, Table, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from zakup.platform.db import metadata

# iiko GUID ↔ bizning ID; har server o'z GUID'lari bilan (DATABASE §2.7)
links = Table(
    "links",
    metadata,
    Column("server_code", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("iiko_id", UUID(as_uuid=True), nullable=False),
    Column("local_id", UUID(as_uuid=True), nullable=False),
    Column("key", Text),  # tabiiy kalit: yetkazuvchi — normallashtirilgan nom, tovar — artikul
    Column("attrs", JSONB, nullable=False, server_default="{}"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    PrimaryKeyConstraint("server_code", "kind", "iiko_id"),
    CheckConstraint("kind IN ('branch', 'store', 'category', 'product', 'supplier')", name="kind"),
    Index("ix_links_kind_iiko_id", "kind", "iiko_id"),
    Index("ix_links_kind_key", "kind", "key", postgresql_where=text("key IS NOT NULL")),
    Index("ix_links_kind_local_id", "kind", "local_id"),
    schema="iiko",
)

sync_runs = Table(
    "sync_runs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("server_code", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="queued"),
    Column("params", JSONB, nullable=False, server_default="{}"),
    Column("stats", JSONB, nullable=False, server_default="{}"),
    Column("error", Text),
    Column("requested_by", UUID(as_uuid=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    CheckConstraint("kind IN ('references', 'purchase_prices')", name="kind"),
    CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name="status"),
    Index("ix_sync_runs_queued", "created_at", postgresql_where=text("status = 'queued'")),
    Index("ix_sync_runs_server_created", "server_code", "created_at"),
    schema="iiko",
)
