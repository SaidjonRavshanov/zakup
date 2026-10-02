from decimal import Decimal

import pytest

from zakup.shared_kernel.ids import uuid7
from zakup.shared_kernel.money import CurrencyMismatchError, Money, Quantity


def test_uuid7_is_version_7_and_time_ordered() -> None:
    ids = [uuid7() for _ in range(1000)]
    assert all(i.version == 7 for i in ids)
    # millisekund ichida tartib kafolatlanmaydi, lekin vaqt prefiksi kamaymaydi
    prefixes = [i.int >> 80 for i in ids]
    assert prefixes == sorted(prefixes)


def test_money_rounds_half_up_to_tiyin() -> None:
    assert Money(Decimal("10.005")).amount == Decimal("10.01")


def test_money_arithmetic_keeps_decimal() -> None:
    total = Money(Decimal("12500")) * 40 + Money(Decimal("0.10"))
    assert total == Money(Decimal("500000.10"))


def test_money_currency_mismatch() -> None:
    with pytest.raises(CurrencyMismatchError):
        _ = Money(Decimal(1), "UZS") + Money(Decimal(1), "USD")


@pytest.mark.parametrize(
    ("expected", "actual", "pct"),
    [("10", "10.5", "5"), ("10", "9", "-10"), ("0", "3", "0")],
)
def test_quantity_deviation(expected: str, actual: str, pct: str) -> None:
    assert Quantity(Decimal(actual), "kg").deviation_pct(Quantity(Decimal(expected), "kg")) == Decimal(pct)
