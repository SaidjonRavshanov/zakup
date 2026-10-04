"""Hisobot SQL'lari: modullar sxemalarini faqat O'QIYDI (read-model, ARCHITECTURE §3 "analytics").

Sana — Toshkent bo'yicha (`AT TIME ZONE 'Asia/Tashkent'`); ombor doirasi — `:stores` (NULL — hammasi).
"""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.analytics.application.reports import (
    ControlItem,
    Period,
    PricePoint,
    ProductPrice,
    StockItem,
    StockOverview,
    Summary,
    SupplierRating,
)

ZERO = Decimal(0)


def _local(column: str) -> str:
    return f"(({column}) AT TIME ZONE 'Asia/Tashkent')::date"


def _scope(alias: str) -> str:
    return f"(CAST(:stores AS uuid[]) IS NULL OR {alias}.store_id = ANY(CAST(:stores AS uuid[])))"


IN_TRANSIT = "('CREATED', 'SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED', 'REAPPROVAL')"

# Eng arzon faol taklif (bazaviy birlik narxi) — "qancha yo'qotdik" va ombor qiymati uchun
BEST_OFFER = """
    SELECT DISTINCT ON (o.product_id) o.product_id, o.price / o.pack_factor AS price, s.name AS supplier
    FROM catalog.supplier_products o JOIN catalog.suppliers s ON s.id = o.supplier_id
    WHERE o.archived_at IS NULL AND s.archived_at IS NULL AND o.pack_factor > 0
    ORDER BY o.product_id, o.price / o.pack_factor
"""

# Qabul qilingan (brak chiqarilgan) qatorlar: [pfrom, to)
RECEIVED_LINES = f"""
    SELECT l.product_id, {_local("r.received_at")} AS day, l.price_fact AS price,
           GREATEST(l.qty_fact - l.qty_defect, 0) AS qty
    FROM receiving.receipt_lines l JOIN receiving.receipts r ON r.id = l.receipt_id
    WHERE {_scope("r")} AND {_local("r.received_at")} >= :pfrom AND {_local("r.received_at")} < :to
      AND l.qty_fact - l.qty_defect > 0
"""

SUMMARY_RECEIPTS = f"""
    SELECT
      COALESCE(SUM(r.total) FILTER (WHERE {_local("r.received_at")} >= :from), 0) AS purchases,
      COALESCE(SUM(r.total) FILTER (WHERE {_local("r.received_at")} < :from), 0) AS purchases_prev,
      COUNT(*) FILTER (WHERE {_local("r.received_at")} >= :from) AS receipts
    FROM receiving.receipts r
    WHERE {_scope("r")} AND {_local("r.received_at")} >= :pfrom AND {_local("r.received_at")} < :to
"""

SUMMARY_LINES = f"""
    SELECT
      COALESCE(SUM(GREATEST(l.price_expected - l.price_fact, 0) * GREATEST(l.qty_fact - l.qty_defect, 0)), 0),
      COALESCE(SUM(GREATEST(l.price_fact - l.price_expected, 0) * GREATEST(l.qty_fact - l.qty_defect, 0)), 0),
      COALESCE(SUM(l.qty_defect * l.price_fact), 0)
    FROM receiving.receipt_lines l JOIN receiving.receipts r ON r.id = l.receipt_id
    WHERE {_scope("r")} AND {_local("r.received_at")} >= :from AND {_local("r.received_at")} < :to
"""

# Bir xil tovarlar bo'yicha o'rtacha narx o'zgarishi — joriy davr summasi bilan og'irlangan
PRICE_INDEX = f"""
    WITH lines AS ({RECEIVED_LINES}),
    cur AS (SELECT product_id, SUM(price * qty) / SUM(qty) AS avg, SUM(price * qty) AS amount
            FROM lines WHERE day >= :from GROUP BY 1),
    prev AS (SELECT product_id, SUM(price * qty) / SUM(qty) AS avg FROM lines WHERE day < :from GROUP BY 1)
    SELECT SUM(cur.amount * (cur.avg / prev.avg - 1)) / NULLIF(SUM(cur.amount), 0) * 100
    FROM cur JOIN prev ON prev.product_id = cur.product_id WHERE prev.avg > 0
"""

SUMMARY_COUNTS = f"""
    SELECT
      (SELECT COUNT(*) FROM procurement.purchase_requests q
        WHERE {_scope("q")} AND q.status = 'PENDING_APPROVAL') AS pending_requests,
      (SELECT COUNT(*) FROM procurement.purchase_requests q
        WHERE {_scope("q")} AND q.status = 'DRAFT' AND q.type = 'auto') AS auto_drafts,
      (SELECT COUNT(*) FROM procurement.purchase_orders po
        WHERE {_scope("po")} AND po.status IN {IN_TRANSIT}) AS in_transit,
      (SELECT COUNT(*) FROM procurement.purchase_orders po
        WHERE {_scope("po")} AND po.status IN {IN_TRANSIT} AND po.delivery_date = :today) AS arriving_today,
      (SELECT COUNT(*) FROM receiving.receipts r WHERE {_scope("r")} AND r.status = 'DISPUTED') AS open_disputes,
      (SELECT COALESCE(SUM(ob.amount - ob.paid), 0) FROM finance.obligations ob
        WHERE {_scope("ob")} AND ob.status IN ('OPEN', 'PARTIALLY_PAID')) AS debt,
      (SELECT COALESCE(SUM(ob.amount - ob.paid), 0) FROM finance.obligations ob
        WHERE {_scope("ob")} AND ob.status IN ('OPEN', 'PARTIALLY_PAID') AND ob.due_date < :today) AS overdue
"""

SUPPLIERS = f"""
    WITH o AS (
      SELECT po.supplier_id, COUNT(*) AS orders,
             AVG(EXTRACT(EPOCH FROM po.responded_at - po.sent_at) / 3600) FILTER (WHERE po.responded_at IS NOT NULL)
               AS response_hours
      FROM procurement.purchase_orders po
      WHERE {_scope("po")} AND po.sent_at IS NOT NULL AND po.status <> 'CANCELLED'
        AND {_local("po.sent_at")} >= :from AND {_local("po.sent_at")} < :to
      GROUP BY 1
    ), rc AS (
      SELECT r.supplier_id, COUNT(*) AS receipts, SUM(r.total) AS amount,
             AVG(CASE WHEN {_local("r.received_at")} <= po.delivery_date THEN 1 ELSE 0 END) AS on_time
      FROM receiving.receipts r JOIN procurement.purchase_orders po ON po.id = r.order_id
      WHERE {_scope("r")} AND {_local("r.received_at")} >= :from AND {_local("r.received_at")} < :to
      GROUP BY 1
    ), ln AS (
      SELECT r.supplier_id, COUNT(*) AS lines,
             SUM(l.qty_defect * l.price_fact) AS defect_value, SUM(l.qty_fact * l.price_fact) AS fact_value,
             COUNT(*) FILTER (WHERE EXISTS (
               SELECT 1 FROM receiving.discrepancies d
               WHERE d.line_id = l.id AND d.kind IN ('qty_under', 'short') AND NOT d.within_tolerance)) AS short_lines,
             COUNT(*) FILTER (WHERE EXISTS (
               SELECT 1 FROM receiving.discrepancies d
               WHERE d.line_id = l.id AND d.kind = 'price_up' AND NOT d.within_tolerance)) AS price_lines
      FROM receiving.receipt_lines l JOIN receiving.receipts r ON r.id = l.receipt_id
      WHERE {_scope("r")} AND {_local("r.received_at")} >= :from AND {_local("r.received_at")} < :to
      GROUP BY 1
    )
    SELECT s.id, s.name, COALESCE(o.orders, 0), COALESCE(rc.receipts, 0), COALESCE(rc.amount, 0),
           COALESCE(ln.short_lines::numeric / NULLIF(ln.lines, 0), 0),
           COALESCE(ln.defect_value / NULLIF(ln.fact_value, 0), 0),
           COALESCE(ln.price_lines::numeric / NULLIF(ln.lines, 0), 0),
           COALESCE(rc.on_time, 1), o.response_hours
    FROM catalog.suppliers s
    LEFT JOIN o ON o.supplier_id = s.id
    LEFT JOIN rc ON rc.supplier_id = s.id
    LEFT JOIN ln ON ln.supplier_id = s.id
    WHERE o.supplier_id IS NOT NULL OR rc.supplier_id IS NOT NULL
"""

PRICES = f"""
    WITH lines AS ({RECEIVED_LINES}),
    cur AS (SELECT product_id, SUM(qty) AS qty, SUM(price * qty) AS amount FROM lines WHERE day >= :from GROUP BY 1),
    prev AS (SELECT product_id, SUM(price * qty) / SUM(qty) AS avg FROM lines WHERE day < :from GROUP BY 1),
    best AS ({BEST_OFFER})
    SELECT p.id, p.name, p.base_unit, cur.qty, cur.amount, cur.amount / cur.qty, prev.avg, best.price, best.supplier,
           GREATEST(cur.amount - best.price * cur.qty, 0)
    FROM cur
    JOIN catalog.products p ON p.id = cur.product_id
    LEFT JOIN prev ON prev.product_id = cur.product_id
    LEFT JOIN best ON best.product_id = cur.product_id
    ORDER BY cur.amount DESC
    LIMIT :limit
"""

PRICE_HISTORY = f"""
    SELECT h.valid_from AS day, s.name, h.price / o.pack_factor AS price, 'offer' AS source
    FROM catalog.supplier_price_history h
    JOIN catalog.supplier_products o ON o.id = h.supplier_product_id
    JOIN catalog.suppliers s ON s.id = o.supplier_id
    WHERE o.product_id = :product AND h.valid_from >= :since AND o.pack_factor > 0
    UNION ALL
    SELECT {_local("r.received_at")}, s.name, l.price_fact, 'receipt'
    FROM receiving.receipt_lines l
    JOIN receiving.receipts r ON r.id = l.receipt_id
    JOIN catalog.suppliers s ON s.id = r.supplier_id
    WHERE l.product_id = :product AND {_local("r.received_at")} >= :since
    ORDER BY 1, 2
"""

# Neliquid: qoldiq bor, kamida 14 kunlik sarf tarixi bor, lekin oynada sarf yo'q
STOCK = f"""
    WITH c AS (
      SELECT store_id, product_id, SUM(qty) AS total FROM planning.consumption_daily
      WHERE day >= CAST(:today AS date) - CAST(:window AS int) AND day < :today GROUP BY 1, 2
    ), f AS (SELECT store_id, MIN(day) AS first_day FROM planning.consumption_daily GROUP BY 1),
    best AS ({BEST_OFFER}),
    items AS (
      SELECT sc.store_id, st.name AS store_name, sc.product_id, p.name, p.base_unit, sc.qty,
             sc.qty * COALESCE(best.price, 0) AS value,
             CASE WHEN f.first_day IS NULL THEN 0
                  ELSE COALESCE(c.total, 0)
                       / GREATEST(LEAST(CAST(:window AS int), CAST(:today AS date) - f.first_day), 1)
             END AS avg_daily,
             f.first_day IS NOT NULL AND f.first_day <= CAST(:today AS date) - 14 AND COALESCE(c.total, 0) = 0 AS dead
      FROM planning.stock_current sc
      JOIN catalog.stores st ON st.id = sc.store_id
      JOIN catalog.products p ON p.id = sc.product_id
      LEFT JOIN c ON c.store_id = sc.store_id AND c.product_id = sc.product_id
      LEFT JOIN f ON f.store_id = sc.store_id
      LEFT JOIN best ON best.product_id = sc.product_id
      WHERE sc.qty > 0 AND {_scope("sc")}
    )
    SELECT *, SUM(value) OVER () AS total_value, COALESCE(SUM(value) FILTER (WHERE dead) OVER (), 0) AS dead_value
    FROM items ORDER BY value DESC LIMIT :limit
"""

CONTROL = f"""
    SELECT 'price_change', po.id, po.number, s.name, st.name,
           SUM((l.price_confirmed - l.price_per_pack) * COALESCE(l.qty_confirmed, l.qty_packs)),
           {_local("COALESCE(po.responded_at, po.created_at)")}
    FROM procurement.purchase_orders po
    JOIN procurement.purchase_order_lines l ON l.order_id = po.id
    JOIN catalog.suppliers s ON s.id = po.supplier_id
    JOIN catalog.stores st ON st.id = po.store_id
    WHERE {_scope("po")} AND l.price_confirmed IS NOT NULL AND l.price_confirmed <> l.price_per_pack
      AND {_local("COALESCE(po.responded_at, po.created_at)")} >= :from
      AND {_local("COALESCE(po.responded_at, po.created_at)")} < :to
    GROUP BY po.id, po.number, s.name, st.name, po.responded_at, po.created_at

    UNION ALL
    SELECT 'discrepancy', r.id, r.number, s.name, string_agg(DISTINCT d.kind, ', '),
           r.total - r.expected_total, {_local("r.received_at")}
    FROM receiving.receipts r
    JOIN receiving.discrepancies d ON d.receipt_id = r.id AND NOT d.within_tolerance AND d.kind <> 'price_down'
    JOIN catalog.suppliers s ON s.id = r.supplier_id
    WHERE {_scope("r")} AND {_local("r.received_at")} >= :from AND {_local("r.received_at")} < :to
    GROUP BY r.id, r.number, s.name, r.total, r.expected_total, r.received_at

    UNION ALL
    SELECT 'role_conflict', q.id, q.number, u.full_name, a.decision, a.amount, {_local("a.decided_at")}
    FROM procurement.approvals a
    JOIN procurement.purchase_requests q ON q.id = a.request_id
    JOIN identity.users u ON u.id = a.approver_id
    WHERE a.role_conflict AND {_scope("q")}
      AND {_local("a.decided_at")} >= :from AND {_local("a.decided_at")} < :to

    UNION ALL
    SELECT 'manual_increase', q.id, q.number, p.name,
           trim_scale(l.qty_suggested)::text || ' → ' || trim_scale(l.qty)::text || ' ' || p.base_unit,
           (l.qty - l.qty_suggested) * l.price_per_base, {_local("q.created_at")}
    FROM procurement.purchase_request_lines l
    JOIN procurement.purchase_requests q ON q.id = l.request_id
    JOIN catalog.products p ON p.id = l.product_id
    WHERE l.qty_suggested IS NOT NULL AND l.qty > l.qty_suggested * 1.2 AND {_scope("q")}
      AND {_local("q.created_at")} >= :from AND {_local("q.created_at")} < :to

    UNION ALL
    SELECT 'payment_without_proof', pr.id, pr.number, s.name, pr.method, pr.total, {_local("pr.paid_at")}
    FROM finance.payment_requests pr JOIN catalog.suppliers s ON s.id = pr.supplier_id
    WHERE pr.status = 'PAID' AND pr.proof_id IS NULL AND CAST(:stores AS uuid[]) IS NULL
      AND {_local("pr.paid_at")} >= :from AND {_local("pr.paid_at")} < :to
"""


class SqlAnalyticsReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _rows(self, sql: str, **params: Any) -> list[Any]:
        return list((await self._session.execute(text(sql), params)).all())

    async def summary(self, *, stores: list[UUID] | None, period: Period, today: date) -> Summary:
        window = {"stores": stores, "from": period.date_from, "to": period.date_to, "pfrom": period.previous.date_from}
        purchases, purchases_prev, receipts = (await self._rows(SUMMARY_RECEIPTS, **window))[0]
        savings, overpay, defect = (
            await self._rows(SUMMARY_LINES, stores=stores, **{"from": period.date_from, "to": period.date_to})
        )[0]
        (index,) = (await self._rows(PRICE_INDEX, **window))[0]
        counts = (await self._rows(SUMMARY_COUNTS, stores=stores, today=today))[0]
        return Summary(
            period=period,
            purchases=purchases,
            purchases_prev=purchases_prev,
            receipts=receipts,
            savings=savings,
            overpay=overpay,
            defect_loss=defect,
            price_change_pct=Decimal(index).quantize(Decimal("0.1")) if index is not None else None,
            pending_requests=counts.pending_requests,
            auto_drafts=counts.auto_drafts,
            orders_in_transit=counts.in_transit,
            arriving_today=counts.arriving_today,
            open_disputes=counts.open_disputes,
            debt=counts.debt,
            overdue=counts.overdue,
        )

    async def suppliers(self, *, stores: list[UUID] | None, period: Period) -> list[SupplierRating]:
        rows = await self._rows(SUPPLIERS, stores=stores, **{"from": period.date_from, "to": period.date_to})
        return [
            SupplierRating(
                supplier_id=r[0],
                supplier_name=r[1],
                orders=r[2],
                receipts=r[3],
                amount=r[4],
                short_rate=r[5],
                defect_rate=r[6],
                price_rate=r[7],
                on_time_rate=Decimal(r[8]),
                response_hours=Decimal(r[9]).quantize(Decimal("0.1")) if r[9] is not None else None,
            )
            for r in rows
        ]

    async def prices(self, *, stores: list[UUID] | None, period: Period, limit: int) -> list[ProductPrice]:
        rows = await self._rows(
            PRICES,
            stores=stores,
            limit=limit,
            **{"from": period.date_from, "to": period.date_to, "pfrom": period.previous.date_from},
        )
        return [
            ProductPrice(
                product_id=r[0],
                product_name=r[1],
                base_unit=r[2],
                qty=r[3],
                amount=r[4],
                avg_price=r[5],
                prev_avg_price=r[6],
                best_price=r[7],
                best_supplier=r[8],
                overpay=r[9] or ZERO,
            )
            for r in rows
        ]

    async def price_history(self, product_id: UUID, *, since: date) -> list[PricePoint]:
        rows = await self._rows(PRICE_HISTORY, product=product_id, since=since)
        return [PricePoint(day=r[0], supplier_name=r[1], price=r[2], source=r[3]) for r in rows]

    async def stock(self, *, stores: list[UUID] | None, today: date, window_days: int, limit: int) -> StockOverview:
        rows = await self._rows(STOCK, stores=stores, today=today, window=window_days, limit=limit)
        items = tuple(
            StockItem(
                store_id=r.store_id,
                store_name=r.store_name,
                product_id=r.product_id,
                product_name=r.name,
                base_unit=r.base_unit,
                qty=r.qty,
                value=Decimal(r.value).quantize(Decimal(1)),
                avg_daily=Decimal(r.avg_daily).quantize(Decimal("0.01")),
                days_cover=(r.qty / r.avg_daily).quantize(Decimal("0.1")) if r.avg_daily else None,
                dead=r.dead,
            )
            for r in rows
        )
        total = Decimal(rows[0].total_value).quantize(Decimal(1)) if rows else ZERO
        dead = Decimal(rows[0].dead_value).quantize(Decimal(1)) if rows else ZERO
        return StockOverview(total_value=total, dead_value=dead, items=items)

    async def control(self, *, stores: list[UUID] | None, period: Period) -> list[ControlItem]:
        rows = await self._rows(CONTROL, stores=stores, **{"from": period.date_from, "to": period.date_to})
        return [
            ControlItem(
                kind=r[0], entity_id=r[1], number=r[2], title=r[3], detail=str(r[4] or ""), amount=r[5], at=r[6]
            )
            for r in rows
        ]
