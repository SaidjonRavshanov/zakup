"""Bot xabarlari matni (uz/ru). Toza funksiyalar: fakt'lar → HTML matn (Telegram parse_mode=HTML).

Har xabar qisqa: nima bo'ldi + bitta qatorda tafsilot; hujjatga — "Ochish" tugmasi (Mini App).
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from html import escape


class Kind(StrEnum):
    REQUEST_PENDING = "request_pending"
    REQUEST_APPROVED = "request_approved"
    REQUEST_PARTIAL = "request_partial"
    REQUEST_RETURNED = "request_returned"
    REQUEST_REJECTED = "request_rejected"
    AUTO_DRAFT = "auto_draft"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_REAPPROVAL = "order_reapproval"
    ORDER_CHANGES_APPROVED = "order_changes_approved"
    RECEIPT_DISPUTED = "receipt_disputed"
    PAYMENT_TO_APPROVE = "payment_to_approve"
    PAYMENT_TO_PAY = "payment_to_pay"
    PAYMENT_REJECTED = "payment_rejected"
    PAYMENT_PAID = "payment_paid"
    USER_PENDING = "user_pending"
    USER_ACTIVATED = "user_activated"
    DELIVERIES_TODAY = "deliveries_today"


@dataclass(frozen=True, slots=True)
class Facts:
    """Xabar uchun ma'lumot: hammasi ixtiyoriy, shablon keraklisini oladi."""

    number: str = ""
    store: str = ""
    supplier: str = ""
    amount: str = ""
    day: date | None = None
    lines: int = 0
    comment: str = ""
    name: str = ""
    telegram_id: int = 0
    items: tuple[str, ...] = ()


BUTTON = {"ru": "Открыть", "uz": "Ochish"}

_TEMPLATES: dict[Kind, dict[str, str]] = {
    Kind.REQUEST_PENDING: {
        "ru": "📝 <b>Заявка {number} ждёт утверждения</b>\n{store} · {amount} · нужно к {day}",
        "uz": "📝 <b>{number} zayavka tasdiqlashni kutmoqda</b>\n{store} · {amount} · {day} gacha",
    },
    Kind.REQUEST_APPROVED: {
        "ru": "✅ <b>Заявка {number} утверждена</b> — заказы поставщикам созданы\n{store}",
        "uz": "✅ <b>{number} zayavka tasdiqlandi</b> — yetkazuvchilarga buyurtmalar yaratildi\n{store}",
    },
    Kind.REQUEST_PARTIAL: {
        "ru": "✅ <b>Заявка {number} утверждена частично</b>\n{store}",
        "uz": "✅ <b>{number} zayavka qisman tasdiqlandi</b>\n{store}",
    },
    Kind.REQUEST_RETURNED: {
        "ru": "↩️ <b>Заявка {number} возвращена на доработку</b>\n{comment}",
        "uz": "↩️ <b>{number} zayavka qayta ishlashga qaytarildi</b>\n{comment}",
    },
    Kind.REQUEST_REJECTED: {
        "ru": "❌ <b>Заявка {number} отклонена</b>\n{comment}",
        "uz": "❌ <b>{number} zayavka rad etildi</b>\n{comment}",
    },
    Kind.AUTO_DRAFT: {
        "ru": "🤖 <b>Автозаявка {number} готова</b> — проверьте и отправьте\n{store} · {lines} поз. · {amount}",
        "uz": "🤖 <b>{number} avto-zayavka tayyor</b> — tekshirib yuboring\n{store} · {lines} poz. · {amount}",
    },
    Kind.ORDER_CONFIRMED: {
        "ru": "📦 <b>{supplier} подтвердил заказ {number}</b>\n{store} · поставка {day}",
        "uz": "📦 <b>{supplier} {number} buyurtmani tasdiqladi</b>\n{store} · yetkazish {day}",
    },
    Kind.ORDER_REAPPROVAL: {
        "ru": "⚠️ <b>{supplier} изменил цену в заказе {number}</b> — нужно переутверждение\n{store} · {amount}",
        "uz": "⚠️ <b>{supplier} {number} buyurtmada narxni o'zgartirdi</b> — qayta tasdiqlash kerak\n{store} · {amount}",
    },
    Kind.ORDER_CHANGES_APPROVED: {
        "ru": "✅ <b>Изменения в заказе {number} утверждены</b>\n{supplier} · {store} · {amount}",
        "uz": "✅ <b>{number} buyurtmadagi o'zgarishlar tasdiqlandi</b>\n{supplier} · {store} · {amount}",
    },
    Kind.RECEIPT_DISPUTED: {
        "ru": "⚠️ <b>Спор по приёмке {number}</b>\n{supplier} · {store} · {amount}",
        "uz": "⚠️ <b>{number} qabul bo'yicha nizo</b>\n{supplier} · {store} · {amount}",
    },
    Kind.PAYMENT_TO_APPROVE: {
        "ru": "💳 <b>Оплата {number} ждёт утверждения</b>\n{supplier} · {amount}",
        "uz": "💳 <b>{number} to'lov tasdiqlashni kutmoqda</b>\n{supplier} · {amount}",
    },
    Kind.PAYMENT_TO_PAY: {
        "ru": "💰 <b>К оплате: {number}</b>\n{supplier} · {amount}",
        "uz": "💰 <b>To'lash kerak: {number}</b>\n{supplier} · {amount}",
    },
    Kind.PAYMENT_REJECTED: {
        "ru": "❌ <b>Оплата {number} отклонена</b>\n{supplier} · {comment}",
        "uz": "❌ <b>{number} to'lov rad etildi</b>\n{supplier} · {comment}",
    },
    Kind.PAYMENT_PAID: {
        "ru": "✅ <b>Оплата {number} проведена</b>\n{supplier} · {amount}",
        "uz": "✅ <b>{number} to'lov amalga oshirildi</b>\n{supplier} · {amount}",
    },
    Kind.USER_PENDING: {
        "ru": "👤 <b>Новый сотрудник ждёт доступа</b>\n{name} · ID {telegram_id}",
        "uz": "👤 <b>Yangi xodim ruxsat kutmoqda</b>\n{name} · ID {telegram_id}",
    },
    Kind.USER_ACTIVATED: {
        "ru": "✅ <b>Доступ открыт.</b> Откройте приложение кнопкой ниже.",
        "uz": "✅ <b>Ruxsat berildi.</b> Ilovani quyidagi tugma orqali oching.",
    },
    Kind.DELIVERIES_TODAY: {
        "ru": "🚚 <b>Сегодня поставок: {lines}</b> · {store}\n{items}",
        "uz": "🚚 <b>Bugun yetkazmalar: {lines}</b> · {store}\n{items}",
    },
}

_CURRENCY = {"ru": "сум", "uz": "so'm"}


def money(value: str, locale: str) -> str:
    """ "1250000.50" → "1 250 001 сум" (so'mda tiyin ko'rsatilmaydi)."""
    try:
        whole = int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return value
    return f"{whole:,}".replace(",", " ") + f" {_CURRENCY[locale]}"


def _day(value: date | None) -> str:
    return value.strftime("%d.%m") if value else "—"


def render(kind: Kind, locale: str, facts: Facts) -> str:
    lang = locale if locale in ("ru", "uz") else "ru"
    text = _TEMPLATES[kind][lang].format(
        number=escape(facts.number),
        store=escape(facts.store),
        supplier=escape(facts.supplier),
        amount=money(facts.amount, lang) if facts.amount else "—",
        day=_day(facts.day),
        lines=facts.lines,
        comment=escape(facts.comment) or "—",
        name=escape(facts.name),
        telegram_id=facts.telegram_id,
        items="\n".join(f"• {escape(item)}" for item in facts.items),
    )
    return text.rstrip()
