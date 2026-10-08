"""receiving: qabulda "В долг / Оплачено на месте" — joyida to'langan nakladnoy majburiyati darhol yopiladi

Eski qabullar — qarzga (false).

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "receipts",
        sa.Column("paid_on_delivery", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="receiving",
    )


def downgrade() -> None:
    op.drop_column("receipts", "paid_on_delivery", schema="receiving")
