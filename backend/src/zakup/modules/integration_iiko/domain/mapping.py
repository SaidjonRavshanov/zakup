"""iiko ma'lumotlarini bizning ma'lumotnomaga moslash qoidalari — sof funksiyalar, testlanadi."""

import re
from dataclasses import dataclass
from enum import StrEnum

from zakup.modules.integration_iiko.domain.models import IikoProduct, IikoUnit

# OKEI kodlari (iiko MeasureUnit.code) va nomlari → bizning birlik kodlari (catalog.domain.product.Unit)
_UNIT_BY_CODE = {"166": "kg", "163": "g", "112": "l", "111": "ml", "796": "pcs"}
_UNIT_BY_NAME = {
    "кг": "kg",
    "г": "g",
    "гр": "g",
    "л": "l",
    "мл": "ml",
    "шт": "pcs",
    "kg": "kg",
    "l": "l",
    "dona": "pcs",
}

PURCHASABLE_TYPES = frozenset({"GOODS"})


def unit_code(unit: IikoUnit) -> str | None:
    """None — tanilmagan birlik (masalan, "порц"): bunday tovar xaridga olinmaydi."""
    if unit.code and unit.code in _UNIT_BY_CODE:
        return _UNIT_BY_CODE[unit.code]
    return _UNIT_BY_NAME.get(unit.name.strip().lower().rstrip("."))


def is_purchasable(product: IikoProduct) -> bool:
    return product.type in PURCHASABLE_TYPES and not product.deleted


class PaymentMethod(StrEnum):
    CASH = "cash"  # НАЛ
    TRANSFER = "transfer"  # ПЕР — perechislenie


@dataclass(frozen=True, slots=True)
class SupplierName:
    """iiko'da bitta yetkazib beruvchi to'lov usuli bo'yicha ikki kartochka: "НАЛ Aziz aka" va "(ПЕР) Aziz aka".
    Zakup uchun bu bitta yetkazib beruvchi, to'lov usuli — nakladnoy / to'lov belgisi
    (foydalanuvchi qarori, 2026-10-03)."""

    display: str
    key: str
    payment_method: PaymentMethod | None


_METHODS = {"нал": PaymentMethod.CASH, "пер": PaymentMethod.TRANSFER}
_MARK = r"(нал|пер)\.?"
_PREFIX = re.compile(rf"^\s*(?:\(\s*{_MARK}\s*\)|{_MARK}(?=\s))\s*", re.IGNORECASE)
_SUFFIX = re.compile(rf"\s*(?:\(\s*{_MARK}\s*\)|(?<=\s){_MARK})\s*$", re.IGNORECASE)
# O'rtada: "(пер)" qavsda yoki alohida so'z sifatida KATTA harflar bilan ("Анвар ака НАЛ (от гошти)").
# "Перчатка", "Персонал" kabi so'zlar tegilmaydi.
_INFIX = re.compile(r"\s*(?:\((?i:\s*(нал|пер)\s*)\)|(?<!\w)(НАЛ|ПЕР)(?!\w))\s*")
_KEY_DROP = re.compile(r"[\"'«»“”„`()\s.,]+")


def parse_supplier_name(raw: str) -> SupplierName:
    name = " ".join(raw.split())
    method: PaymentMethod | None = None
    for pattern in (_PREFIX, _SUFFIX, _INFIX):
        if pattern is _INFIX and method is not None:
            break
        match = pattern.search(name)
        if match:
            mark = next(g for g in match.groups() if g)
            method = method or _METHODS[mark.lower()]
            name = (name[: match.start()] + " " + name[match.end() :]).strip()
    name = _unwrap_parentheses(name)
    return SupplierName(
        display=name or raw.strip(), key=_KEY_DROP.sub(" ", name.lower()).strip(), payment_method=method
    )


def payment_method_from_comment(comment: str | None) -> PaymentMethod | None:
    """Nakladnoy izohi: "нал" / "пер" (Sebzar: 37 / 42 nakladnoyda shunday)."""
    return _METHODS.get((comment or "").strip().lower().rstrip("."))


def _unwrap_parentheses(name: str) -> str:
    """'(OOO "HORECA Partners ")' → 'OOO "HORECA Partners "' — faqat butun nom qavsda bo'lsa."""
    while name.startswith("(") and name.endswith(")") and _balanced(name[1:-1]):
        name = name[1:-1].strip()
    return name


def _balanced(text: str) -> bool:
    depth = 0
    for char in text:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if depth < 0:
            return False
    return depth == 0
