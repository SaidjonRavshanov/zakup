"""Transactional outbox (ADR-04): event biznes o'zgarishi bilan bitta tranzaksiyada yoziladi,
worker keyin `FOR UPDATE SKIP LOCKED` bilan o'qib, iiko / Telegram / PDF ga yuboradi."""

import dataclasses
import json
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Index, Integer, Table, Text, func, insert, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.platform.db import metadata
from zakup.shared_kernel.events import DomainEvent

outbox = Table(
    "outbox",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("aggregate_type", Text, nullable=False),
    Column("aggregate_id", UUID(as_uuid=True), nullable=False),
    Column("event_type", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("processed_at", DateTime(timezone=True)),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("next_attempt_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("last_error", Text),
    Index("ix_outbox_pending", "next_attempt_at", postgresql_where=text("processed_at IS NULL")),
    schema="platform",
)


def _json_default(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def serialize(event: DomainEvent) -> dict[str, Any]:
    raw = dataclasses.asdict(event)
    loaded: dict[str, Any] = json.loads(json.dumps(raw, default=_json_default))
    return loaded


async def write_events(session: AsyncSession, aggregate_type: str, events: list[DomainEvent]) -> None:
    if not events:
        return
    await session.execute(
        insert(outbox),
        [
            {
                "id": event.event_id,
                "aggregate_type": aggregate_type,
                "aggregate_id": event.aggregate_id,
                "event_type": event.event_type,
                "payload": serialize(event),
            }
            for event in events
        ],
    )
