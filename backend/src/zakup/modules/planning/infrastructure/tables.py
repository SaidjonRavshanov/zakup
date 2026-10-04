from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Numeric, Table
from sqlalchemy.dialects.postgresql import UUID

from zakup.platform.db import metadata

# Oxirgi qoldiq (iiko balance/stores snapshot'i): tarix kerak bo'lsa — keyin oy bo'yicha partitsiyalangan jadval
stock_current = Table(
    "stock_current",
    metadata,
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), primary_key=True),
    Column("qty", Numeric(18, 4), nullable=False),
    Column("taken_at", DateTime(timezone=True), nullable=False),
    schema="planning",
)

# Kunlik sarf (iiko OLAP TRANSACTIONS) — bazaviy birlikda
consumption_daily = Table(
    "consumption_daily",
    metadata,
    Column("store_id", UUID(as_uuid=True), ForeignKey("catalog.stores.id"), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("catalog.products.id"), primary_key=True),
    Column("day", Date, primary_key=True),
    Column("qty", Numeric(18, 4), nullable=False),
    Index("ix_consumption_daily_store_day", "store_id", "day"),
    schema="planning",
)
