"""Yetkazuvchi balli: ayirilgan ballar yig'indisi = 100 - ball (ekrandagi izoh ball bilan mos)."""

from decimal import Decimal

from zakup.modules.analytics.domain.rating import score_penalties, supplier_score


def test_penalties_explain_score() -> None:
    rates = {
        "short_rate": Decimal("0.25"),
        "defect_rate": Decimal("0.1"),
        "price_rate": Decimal("0.5"),
        "on_time_rate": Decimal("0.8"),
    }
    penalties = score_penalties(**rates)
    assert penalties == {"short": Decimal(10), "defect": Decimal(3), "price": Decimal(10), "late": Decimal(2)}
    assert supplier_score(**rates) == Decimal(100) - sum(penalties.values())


def test_perfect_supplier_has_no_penalties() -> None:
    zero, one = Decimal(0), Decimal(1)
    penalties = score_penalties(short_rate=zero, defect_rate=zero, price_rate=zero, on_time_rate=one)
    assert set(penalties.values()) == {zero}
    assert supplier_score(short_rate=zero, defect_rate=zero, price_rate=zero, on_time_rate=one) == 100
