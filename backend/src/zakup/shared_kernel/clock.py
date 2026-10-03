"""Joriy vaqt manbai — use case'larga inject qilinadi, testda soxta soat beriladi."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def business_today(clock: Clock = utc_now) -> date:
    """Biznes sanasi Toshkent vaqtida (UTC+5, DST yo'q): narx amal qilish sanasi va h.k."""
    return (clock() + timedelta(hours=5)).date()
