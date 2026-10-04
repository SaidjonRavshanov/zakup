"""Yetkazuvchiga yuboriladigan buyurtma matni (Telegram / WhatsApp). Tarnov yetkazuvchilari — rus tilida.

Pozitsiyalar **yetkazuvchi birligida** (qop, quti) va kerak bo'lsa bazaviy miqdor bilan (WORKFLOW B6.4).
"""

from decimal import Decimal

from zakup.modules.procurement.application.dto import OrderDetail

_UNIT_RU = {"kg": "кг", "g": "г", "l": "л", "ml": "мл", "pcs": "шт", "pack": "уп", "box": "кор", "bag": "меш"}


def _num(value: Decimal) -> str:
    text = f"{value.normalize():f}"
    return text.replace(".", ",")


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal(1)):,}".replace(",", " ")


def order_message(order: OrderDetail, *, url: str, company: str) -> str:
    lines = [
        f"Заказ {order.number} — {company}",
        f"Склад: {order.store_name or '—'}",
        f"Доставка: {order.delivery_date:%d.%m.%Y}",
        "",
    ]
    for i, line in enumerate(order.lines, start=1):
        pack = _UNIT_RU.get(line.pack_unit, line.pack_unit)
        base = _UNIT_RU.get(line.base_unit, line.base_unit)
        text = f"{i}. {line.product_name} — {_num(line.qty_packs)} {pack}"
        if line.pack_unit != line.base_unit or line.pack_factor != 1:
            text += f" ({_num(line.qty_packs * line.pack_factor)} {base})"
        text += f" × {_money(line.price_per_pack)} = {_money(line.amount)} сум"
        lines.append(text)
    lines += ["", f"Итого: {_money(order.total)} сум", "", f"Подтвердите заказ по ссылке: {url}"]
    return "\n".join(lines)
