"""Yetkazuvchi reytingi (WORKFLOW B14): kam yetkazish, brak, narx og'ishi, muddatga rioya — 0..100 ball."""

from decimal import ROUND_HALF_UP, Decimal

# Og'irliklar: kam yetkazish va brak oshxonaga eng ko'p zarar qiladi
WEIGHTS = {"short": Decimal(40), "defect": Decimal(30), "price": Decimal(20), "late": Decimal(10)}


def score_penalties(
    *, short_rate: Decimal, defect_rate: Decimal, price_rate: Decimal, on_time_rate: Decimal
) -> dict[str, Decimal]:
    """Har bir ko'rsatkich qancha ball ayirgani (ekranda "nega shu ball" uchun). Ulushlar 0..1."""
    return {
        "short": WEIGHTS["short"] * _clamp(short_rate),
        "defect": WEIGHTS["defect"] * _clamp(defect_rate),
        "price": WEIGHTS["price"] * _clamp(price_rate),
        "late": WEIGHTS["late"] * (1 - _clamp(on_time_rate)),
    }


def supplier_score(*, short_rate: Decimal, defect_rate: Decimal, price_rate: Decimal, on_time_rate: Decimal) -> Decimal:
    """Hammasi ideal — 100; har bir ulush o'z og'irligiga qadar ayiradi."""
    penalty = sum(
        score_penalties(
            short_rate=short_rate, defect_rate=defect_rate, price_rate=price_rate, on_time_rate=on_time_rate
        ).values(),
        Decimal(0),
    )
    return max(Decimal(100) - penalty, Decimal(0)).quantize(Decimal(1), ROUND_HALF_UP)


def change_pct(current: Decimal | None, previous: Decimal | None) -> Decimal | None:
    if current is None or not previous:
        return None
    return ((current / previous - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)


def _clamp(value: Decimal) -> Decimal:
    return min(max(value, Decimal(0)), Decimal(1))
