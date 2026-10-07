"""procurement: zayavka qatorida taklif qadog'i — summa buyurtmadagidek qadoqqa yaxlitlanadi

Eski qatorlar: qadoq ma'lumoti hozirgi taklifdan, qadoq narxi — saqlangan bazaviy narxdan (yangi narx olinmaydi).
Ochiq zayavkalar (qoralama / kelishuvda) jami summasi qayta hisoblanadi.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINES = "procurement.purchase_request_lines"


def upgrade() -> None:
    op.add_column("purchase_request_lines", sa.Column("pack_unit", sa.Text(), nullable=True), schema="procurement")
    op.add_column(
        "purchase_request_lines", sa.Column("pack_factor", sa.Numeric(18, 4), nullable=True), schema="procurement"
    )
    op.add_column(
        "purchase_request_lines", sa.Column("pack_multiple", sa.Numeric(18, 4), nullable=True), schema="procurement"
    )
    op.add_column(
        "purchase_request_lines", sa.Column("price_per_pack", sa.Numeric(18, 4), nullable=True), schema="procurement"
    )
    op.execute(
        f"""
        UPDATE {LINES} l
        SET pack_unit = o.pack_unit,
            pack_factor = o.pack_factor,
            pack_multiple = o.order_multiple,
            price_per_pack = round(l.price_per_base * o.pack_factor, 4)
        FROM catalog.supplier_products o
        WHERE o.id = l.offer_id AND l.price_per_base IS NOT NULL
        """  # noqa: S608 — konstanta
    )
    op.execute(
        f"""
        UPDATE procurement.purchase_requests r
        SET total_amount = COALESCE((
            SELECT sum(
                CASE WHEN l.price_per_pack IS NOT NULL THEN
                    round(ceil(l.qty / l.pack_factor / l.pack_multiple) * l.pack_multiple * l.price_per_pack, 2)
                ELSE round(l.qty * COALESCE(l.price_per_base, 0), 2) END)
            FROM {LINES} l WHERE l.request_id = r.id
        ), 0)
        WHERE r.status IN ('DRAFT', 'PENDING_APPROVAL')
        """  # noqa: S608 — konstanta
    )


def downgrade() -> None:
    for column in ("price_per_pack", "pack_multiple", "pack_factor", "pack_unit"):
        op.drop_column("purchase_request_lines", column, schema="procurement")
