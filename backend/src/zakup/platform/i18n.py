"""Foydalanuvchiga ko'rinadigan matnlar katalogi (uz / ru).

Domen va application qatlamlari faqat kalit + parametr beradi; tarjima shu yerda.
Yangi kalit qo'shilganda ikkala til ham to'ldirilishi shart — `tests/unit/test_i18n.py` tekshiradi.
"""

from typing import Final, Literal, get_args

Locale = Literal["uz", "ru"]
LOCALES: Final[tuple[Locale, ...]] = get_args(Locale)
DEFAULT_LOCALE: Final[Locale] = "uz"

MESSAGES: Final[dict[str, dict[Locale, str]]] = {
    # --- umumiy
    "domain_error": {"uz": "Biznes qoidasi buzildi", "ru": "Нарушено бизнес-правило"},
    "not_found": {"uz": "Topilmadi", "ru": "Не найдено"},
    "conflict": {
        "uz": "Ma'lumot boshqa foydalanuvchi tomonidan o'zgartirilgan. Sahifani yangilang",
        "ru": "Данные изменены другим пользователем. Обновите страницу",
    },
    "permission_denied": {"uz": "Ruxsat yo'q", "ru": "Нет доступа"},
    "invalid_transition": {"uz": "Bu holatda amalni bajarib bo'lmaydi", "ru": "Действие недоступно в этом статусе"},
    "validation_error": {"uz": "So'rov ma'lumotlari noto'g'ri", "ru": "Некорректные данные запроса"},
    "internal_error": {"uz": "Ichki xato. Keyinroq urinib ko'ring", "ru": "Внутренняя ошибка. Попробуйте позже"},
    # --- shared_kernel
    "currency_mismatch": {
        "uz": "Valyutalar mos emas: {left} va {right}",
        "ru": "Валюты не совпадают: {left} и {right}",
    },
    "unit_mismatch": {"uz": "Birliklar mos emas: {left} va {right}", "ru": "Единицы не совпадают: {left} и {right}"},
    # --- catalog
    "invalid_supplier": {"uz": "Yetkazib beruvchi ma'lumotlari noto'g'ri", "ru": "Некорректные данные поставщика"},
    "duplicate_inn": {
        "uz": "Bu STIR bilan yetkazib beruvchi allaqachon bor",
        "ru": "Поставщик с таким ИНН уже существует",
    },
    "supplier.name_empty": {"uz": "Nomi bo'sh bo'lishi mumkin emas", "ru": "Название не может быть пустым"},
    "supplier.inn_format": {
        "uz": "STIR 9 yoki 14 raqamdan iborat bo'lishi kerak",
        "ru": "ИНН должен состоять из 9 или 14 цифр",
    },
    "supplier.deferral_range": {
        "uz": "Kechiktirish 1 dan {max} kungacha bo'lishi kerak",
        "ru": "Отсрочка должна быть от 1 до {max} дней",
    },
    "supplier.deferral_only_deferred": {
        "uz": "Kechiktirish faqat «kechiktirilgan to'lov» shartida beriladi",
        "ru": "Отсрочка задаётся только для условия «оплата с отсрочкой»",
    },
    "supplier.duplicate_inn": {
        "uz": "STIR {inn} bilan yetkazib beruvchi allaqachon bor",
        "ru": "Поставщик с ИНН {inn} уже существует",
    },
    "supplier.modified": {
        "uz": "Yetkazib beruvchi boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Поставщик изменён другим пользователем",
    },
    # --- auth
    "invalid_init_data": {"uz": "Telegram orqali kirish tasdiqlanmadi", "ru": "Вход через Telegram не подтверждён"},
    "auth.init_data_empty": {"uz": "Telegram ma'lumotlari yo'q", "ru": "Нет данных Telegram"},
    "auth.init_data_no_hash": {"uz": "Telegram imzosi yo'q", "ru": "Отсутствует подпись Telegram"},
    "auth.init_data_bad_signature": {"uz": "Telegram imzosi noto'g'ri", "ru": "Неверная подпись Telegram"},
    "auth.init_data_expired": {
        "uz": "Sessiya eskirgan. Ilovani qayta oching",
        "ru": "Сессия устарела. Откройте приложение заново",
    },
    "auth.init_data_bad_user": {"uz": "Telegram foydalanuvchisi noto'g'ri", "ru": "Некорректный пользователь Telegram"},
    "unauthenticated": {"uz": "Tizimga kiring", "ru": "Требуется вход"},
    "invalid_token": {"uz": "Sessiya yaroqsiz. Qayta kiring", "ru": "Сессия недействительна. Войдите заново"},
    "auth.token_missing": {"uz": "Tizimga kiring", "ru": "Требуется вход"},
    "auth.token_expired": {"uz": "Sessiya muddati tugadi", "ru": "Срок сессии истёк"},
    "auth.token_invalid": {"uz": "Sessiya yaroqsiz. Qayta kiring", "ru": "Сессия недействительна. Войдите заново"},
    "invalid_refresh_token": {"uz": "Sessiya yaroqsiz. Qayta kiring", "ru": "Сессия недействительна. Войдите заново"},
    "auth.refresh_invalid": {"uz": "Sessiya yaroqsiz. Qayta kiring", "ru": "Сессия недействительна. Войдите заново"},
    "auth.refresh_expired": {
        "uz": "Sessiya muddati tugadi. Ilovani qayta oching",
        "ru": "Срок сессии истёк. Откройте приложение заново",
    },
    "auth.role_required": {
        "uz": "Bu amal uchun sizning rolingizda ruxsat yo'q",
        "ru": "У вашей роли нет прав на это действие",
    },
    "account_pending": {
        "uz": "Akkaunt hali faollashtirilmagan",
        "ru": "Аккаунт ещё не активирован",
    },
    "auth.account_pending": {
        "uz": "Akkauntingiz administrator tasdig'ini kutmoqda",
        "ru": "Ваш аккаунт ожидает подтверждения администратором",
    },
    # --- identity
    "invalid_user": {"uz": "Foydalanuvchi ma'lumotlari noto'g'ri", "ru": "Некорректные данные пользователя"},
    "user.telegram_id": {"uz": "Telegram ID noto'g'ri", "ru": "Некорректный Telegram ID"},
    "user.too_many_grants": {
        "uz": "Rollar soni {max} tadan oshmasligi kerak",
        "ru": "Ролей не может быть больше {max}",
    },
    "user.not_found": {"uz": "Foydalanuvchi topilmadi", "ru": "Пользователь не найден"},
    "user.modified": {
        "uz": "Foydalanuvchi boshqa administrator tomonidan o'zgartirilgan",
        "ru": "Пользователь изменён другим администратором",
    },
    "self_lockout": {"uz": "O'zingizni bloklab bo'lmaydi", "ru": "Нельзя заблокировать самого себя"},
    "user.self_deactivate": {"uz": "O'zingizni o'chira olmaysiz", "ru": "Нельзя деактивировать самого себя"},
    "user.self_remove_admin": {
        "uz": "O'zingizdan administrator rolini olib bo'lmaydi",
        "ru": "Нельзя снять роль администратора с самого себя",
    },
}


def negotiate_locale(accept_language: str | None) -> Locale:
    """`Accept-Language: ru-RU,ru;q=0.9,en;q=0.8` → 'ru'. Qo'llab-quvvatlanmasa — DEFAULT_LOCALE."""
    if not accept_language:
        return DEFAULT_LOCALE
    ranked: list[tuple[float, str]] = []
    for part in accept_language.split(","):
        lang, _, q = part.strip().partition(";q=")
        try:
            weight = float(q) if q else 1.0
        except ValueError:
            weight = 0.0
        ranked.append((weight, lang.split("-")[0].lower()))
    for _, lang in sorted(ranked, key=lambda item: -item[0]):
        if lang in LOCALES:
            return lang
    return DEFAULT_LOCALE


def translate(key: str, locale: Locale, params: dict[str, object] | None = None) -> str:
    entry = MESSAGES.get(key)
    if entry is None:
        return key  # katalogda yo'q kalit — test buni ushlaydi, prod'da hech bo'lmasa kalit ko'rinadi
    text = entry[locale]
    try:
        return text.format(**(params or {}))
    except (KeyError, IndexError):
        return text
