"""Ehtiyoj hisobi (WORKFLOW B3) — sof funksiyalar, framework'siz.

    Ehtiyoj = O'rtachaSarf x (YetkazishMuddati + QoplashDavri) + Sug'urtaZaxira - Qoldiq - Yo'lda
    Buyurtma nuqtasi = O'rtachaSarf x YetkazishMuddati + Sug'urtaZaxira

Qadoqqa yaxlitlash — chaqiruvchida (yetkazuvchi taklifi catalog'da).
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal(0)
QTY = Decimal("0.0001")


def average_daily(total: Decimal, *, window_days: int, first_day: date | None, today: date) -> tuple[Decimal, int]:
    """O'rtacha kunlik sarf va haqiqatda kuzatilgan kunlar soni.

    Tarix oynadan qisqa bo'lsa (tizim endi ulandi) — mavjud kunlarga bo'linadi; ma'lumot umuman yo'q — 0 kun.
    Oyna: [today - window_days, today) — bugungi to'liq bo'lmagan kun hisobga olinmaydi.
    """
    if first_day is None or first_day >= today:
        return ZERO, 0
    days = min(window_days, (today - first_day).days)
    return (total / days).quantize(QTY, ROUND_HALF_UP), days


@dataclass(frozen=True, slots=True)
class DemandInputs:
    avg_daily: Decimal
    stock: Decimal  # iiko qoldig'i (manfiy bo'lishi mumkin — 0 deb olinadi)
    in_transit: Decimal  # yuborilgan, hali qabul qilinmagan buyurtmalar
    lead_days: int
    coverage_days: int
    safety_stock: Decimal
    seasonal_factor: Decimal = Decimal(1)


@dataclass(frozen=True, slots=True)
class DemandResult:
    daily: Decimal  # mavsumiy koeffitsient bilan
    target: Decimal  # yetkazish + qoplash davriga kerak bo'ladigan zaxira
    available: Decimal  # qoldiq + yo'lda
    reorder_point: Decimal
    need: Decimal  # >= 0

    @property
    def below_reorder_point(self) -> bool:
        return self.available <= self.reorder_point


def calculate(inputs: DemandInputs) -> DemandResult:
    daily = (inputs.avg_daily * inputs.seasonal_factor).quantize(QTY, ROUND_HALF_UP)
    target = daily * (inputs.lead_days + inputs.coverage_days) + inputs.safety_stock
    available = max(inputs.stock, ZERO) + inputs.in_transit
    return DemandResult(
        daily=daily,
        target=target.quantize(QTY, ROUND_HALF_UP),
        available=available,
        reorder_point=(daily * inputs.lead_days + inputs.safety_stock).quantize(QTY, ROUND_HALF_UP),
        need=max(target - available, ZERO).quantize(QTY, ROUND_HALF_UP),
    )
