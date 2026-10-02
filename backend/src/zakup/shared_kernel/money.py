"""Pul va miqdor — faqat Decimal, hech qachon float (ADR-09)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Self

from zakup.shared_kernel.errors import DomainError

_MONEY_EXP = Decimal("0.01")
_QTY_EXP = Decimal("0.0001")


class CurrencyMismatchError(DomainError):
    code = "currency_mismatch"


class UnitMismatchError(DomainError):
    code = "unit_mismatch"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "UZS"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", Decimal(self.amount).quantize(_MONEY_EXP, ROUND_HALF_UP))

    @classmethod
    def zero(cls, currency: str = "UZS") -> Self:
        return cls(Decimal(0), currency)

    def _check(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(left=self.currency, right=other.currency)

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int) -> "Money":
        return Money(self.amount * Decimal(factor), self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._check(other)
        return self.amount <= other.amount

    def is_negative(self) -> bool:
        return self.amount < 0


@dataclass(frozen=True, slots=True)
class Quantity:
    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", Decimal(self.value).quantize(_QTY_EXP, ROUND_HALF_UP))

    def deviation_pct(self, expected: "Quantity") -> Decimal:
        """Kutilganidan og'ish, % (dopusk tekshiruvi uchun, WORKFLOW B9)."""
        if expected.unit != self.unit:
            raise UnitMismatchError(left=self.unit, right=expected.unit)
        if expected.value == 0:
            return Decimal(0)
        return (self.value - expected.value) / expected.value * 100
