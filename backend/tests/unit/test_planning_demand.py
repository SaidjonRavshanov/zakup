from datetime import date
from decimal import Decimal

from zakup.modules.planning.domain.demand import DemandInputs, average_daily, calculate

TODAY = date(2026, 10, 4)


def test_average_uses_window_or_shorter_history() -> None:
    assert average_daily(Decimal(280), window_days=28, first_day=date(2026, 8, 1), today=TODAY) == (Decimal(10), 28)
    # Tizim endi ulandi: 10 kunlik tarix — 10 ga bo'linadi (28 ga emas)
    assert average_daily(Decimal(100), window_days=28, first_day=date(2026, 9, 24), today=TODAY) == (Decimal(10), 10)
    assert average_daily(Decimal(0), window_days=28, first_day=None, today=TODAY) == (Decimal(0), 0)


def test_need_formula_and_reorder_point() -> None:
    # 10 kg/kun, yetkazish 1 kun, qoplash 3 kun, zaxira 5: maqsad 45; qoldiq 4 + yo'lda 20 = 24 → ehtiyoj 21
    result = calculate(
        DemandInputs(
            avg_daily=Decimal(10),
            stock=Decimal(4),
            in_transit=Decimal(20),
            lead_days=1,
            coverage_days=3,
            safety_stock=Decimal(5),
        )
    )
    assert (result.target, result.available, result.need, result.reorder_point) == (
        Decimal(45),
        Decimal(24),
        Decimal(21),
        Decimal(15),
    )
    assert not result.below_reorder_point


def test_negative_stock_counts_as_zero_and_seasonal_factor() -> None:
    result = calculate(
        DemandInputs(
            avg_daily=Decimal(10),
            stock=Decimal(-7),  # iiko'da kirim qilinmagan sarf — manfiy qoldiq
            in_transit=Decimal(0),
            lead_days=2,
            coverage_days=2,
            safety_stock=Decimal(0),
            seasonal_factor=Decimal("1.5"),
        )
    )
    assert (result.daily, result.need) == (Decimal(15), Decimal(60))
    assert result.below_reorder_point


def test_no_need_when_enough_stock() -> None:
    result = calculate(
        DemandInputs(
            avg_daily=Decimal(1),
            stock=Decimal(100),
            in_transit=Decimal(0),
            lead_days=1,
            coverage_days=7,
            safety_stock=Decimal(2),
        )
    )
    assert result.need == 0
