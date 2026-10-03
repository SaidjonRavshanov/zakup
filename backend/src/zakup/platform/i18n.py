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
    "supplier.not_found": {"uz": "Yetkazib beruvchi topilmadi", "ru": "Поставщик не найден"},
    "supplier.phone_format": {
        "uz": "Telefon raqami noto'g'ri (masalan, +998901234567)",
        "ru": "Неверный номер телефона (например, +998901234567)",
    },
    "supplier.email_format": {"uz": "E-mail noto'g'ri", "ru": "Неверный e-mail"},
    "supplier.lead_time_range": {
        "uz": "Yetkazish muddati 0 dan {max} kungacha bo'lishi kerak",
        "ru": "Срок поставки должен быть от 0 до {max} дней",
    },
    "supplier.weekdays": {
        "uz": "Kamida bitta hafta kuni tanlanishi kerak",
        "ru": "Нужно выбрать хотя бы один день недели",
    },
    "invalid_store": {"uz": "Ombor ma'lumotlari noto'g'ri", "ru": "Некорректные данные склада"},
    "store.name_empty": {"uz": "Ombor nomi bo'sh bo'lishi mumkin emas", "ru": "Название склада не может быть пустым"},
    "store.name_too_long": {"uz": "Nomi {max} belgidan oshmasin", "ru": "Название не длиннее {max} символов"},
    "store.not_found": {"uz": "Ombor topilmadi", "ru": "Склад не найден"},
    "store.modified": {
        "uz": "Ombor boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Склад изменён другим пользователем",
    },
    "invalid_product": {"uz": "Tovar ma'lumotlari noto'g'ri", "ru": "Некорректные данные товара"},
    "product.name_empty": {"uz": "Tovar nomi bo'sh bo'lishi mumkin emas", "ru": "Название товара не может быть пустым"},
    "product.name_too_long": {"uz": "Nomi {max} belgidan oshmasin", "ru": "Название не длиннее {max} символов"},
    "product.base_unit": {
        "uz": "Bazaviy birlik faqat kg, g, l, ml yoki dona bo'ladi",
        "ru": "Базовая единица — только кг, г, л, мл или шт",
    },
    "product.not_found": {"uz": "Tovar topilmadi", "ru": "Товар не найден"},
    "product.modified": {
        "uz": "Tovar boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Товар изменён другим пользователем",
    },
    "category.name_empty": {"uz": "Kategoriya nomi bo'sh", "ru": "Название категории пустое"},
    "category.budget_negative": {
        "uz": "Byudjet manfiy bo'lishi mumkin emas",
        "ru": "Бюджет не может быть отрицательным",
    },
    "category.not_found": {"uz": "Kategoriya topilmadi", "ru": "Категория не найдена"},
    "category.modified": {
        "uz": "Kategoriya boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Категория изменена другим пользователем",
    },
    "invalid_offer": {"uz": "Taklif ma'lumotlari noto'g'ri", "ru": "Некорректные данные предложения"},
    "duplicate_offer": {"uz": "Bunday taklif allaqachon bor", "ru": "Такое предложение уже есть"},
    "offer.duplicate": {
        "uz": "Bu yetkazib beruvchida shu tovar (shu artikul bilan) allaqachon bor",
        "ru": "У этого поставщика уже есть этот товар (с таким артикулом)",
    },
    "offer.factor_positive": {
        "uz": "Qadoqdagi miqdor 0 dan katta bo'lishi kerak",
        "ru": "Количество в упаковке должно быть больше 0",
    },
    "offer.multiple_positive": {"uz": "Karralilik 0 dan katta bo'lishi kerak", "ru": "Кратность должна быть больше 0"},
    "offer.price_negative": {"uz": "Narx manfiy bo'lishi mumkin emas", "ru": "Цена не может быть отрицательной"},
    "offer.price_backdated": {
        "uz": "Yangi narx sanasi joriy narx sanasidan oldin bo'lishi mumkin emas",
        "ru": "Дата новой цены не может быть раньше даты текущей цены",
    },
    "offer.sku_too_long": {"uz": "Artikul {max} belgidan oshmasin", "ru": "Артикул не длиннее {max} символов"},
    "offer.archived_party": {
        "uz": "Arxivdagi yetkazib beruvchi yoki tovarga taklif qo'shib bo'lmaydi",
        "ru": "Нельзя добавить предложение для архивного поставщика или товара",
    },
    "offer.not_found": {"uz": "Taklif topilmadi", "ru": "Предложение не найдено"},
    "offer.modified": {
        "uz": "Taklif boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Предложение изменено другим пользователем",
    },
    "invalid_purchase_card": {"uz": "Xarid kartochkasi noto'g'ri", "ru": "Некорректная карточка закупа"},
    "card.safety_stock_negative": {
        "uz": "Minimal qoldiq manfiy bo'lishi mumkin emas",
        "ru": "Страховой запас не может быть отрицательным",
    },
    "card.coverage_range": {
        "uz": "Qoplash davri 1 dan {max} kungacha",
        "ru": "Период покрытия — от 1 до {max} дней",
    },
    "card.shelf_life_positive": {"uz": "Yaroqlilik muddati kamida 1 kun", "ru": "Срок годности — минимум 1 день"},
    "card.seasonal_range": {
        "uz": "Mavsumiy koeffitsiyent {min} dan {max} gacha",
        "ru": "Сезонный коэффициент — от {min} до {max}",
    },
    "card.alternative_without_primary": {
        "uz": "Avval asosiy yetkazib beruvchini tanlang",
        "ru": "Сначала выберите основного поставщика",
    },
    "card.same_suppliers": {
        "uz": "Asosiy va muqobil yetkazib beruvchi bir xil bo'lmasin",
        "ru": "Основной и альтернативный поставщик должны различаться",
    },
    "card.auto_needs_supplier": {
        "uz": "Avto-zakup uchun asosiy yetkazib beruvchi kerak",
        "ru": "Для авто-закупа нужен основной поставщик",
    },
    "card.supplier_archived": {"uz": "Yetkazib beruvchi arxivda", "ru": "Поставщик в архиве"},
    "card.modified": {
        "uz": "Kartochka boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Карточка изменена другим пользователем",
    },
    "invalid_branch": {"uz": "Filial ma'lumotlari noto'g'ri", "ru": "Некорректные данные филиала"},
    "branch.name_empty": {"uz": "Filial nomi bo'sh", "ru": "Название филиала пустое"},
    "branch.modified": {
        "uz": "Filial boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Филиал изменён другим пользователем",
    },
    # --- iiko
    "iiko_unavailable": {"uz": "iiko serveri javob bermayapti", "ru": "Сервер iiko не отвечает"},
    "iiko.unavailable": {
        "uz": "iiko serveri bilan aloqa yo'q. Keyinroq urinib ko'ring",
        "ru": "Нет связи с сервером iiko. Попробуйте позже",
    },
    "iiko.bad_status": {"uz": "iiko xato qaytardi (HTTP {status})", "ru": "iiko вернул ошибку (HTTP {status})"},
    "iiko.session_busy": {
        "uz": "iiko ({server}) bilan boshqa sinxronizatsiya ishlayapti",
        "ru": "С iiko ({server}) уже идёт другая синхронизация",
    },
    "iiko_auth": {"uz": "iiko'ga kirib bo'lmadi", "ru": "Не удалось войти в iiko"},
    "iiko.auth_failed": {
        "uz": "iiko ({server}): login yoki parol noto'g'ri, yoki litsenziya band",
        "ru": "iiko ({server}): неверный логин/пароль или лицензия занята",
    },
    "iiko_response": {"uz": "iiko javobi tushunarsiz", "ru": "Непонятный ответ iiko"},
    "iiko.bad_xml": {"uz": "iiko javobi (XML) buzilgan", "ru": "Повреждённый ответ iiko (XML)"},
    "iiko.bad_json": {"uz": "iiko javobi (JSON) buzilgan", "ru": "Повреждённый ответ iiko (JSON)"},
    "iiko.bad_id": {"uz": "iiko javobida noto'g'ri ID: {what}", "ru": "Неверный ID в ответе iiko: {what}"},
    "iiko.bad_number": {"uz": "iiko javobida noto'g'ri son: {value}", "ru": "Неверное число в ответе iiko: {value}"},
    "iiko.server_not_found": {"uz": "Bunday iiko serveri sozlanmagan", "ru": "Такой сервер iiko не настроен"},
    "invalid_sync_request": {"uz": "Sinxronizatsiya so'rovi noto'g'ri", "ru": "Некорректный запрос синхронизации"},
    "iiko.days_range": {"uz": "Davr 1 dan {max} kungacha", "ru": "Период — от 1 до {max} дней"},
    "iiko.sync_pending": {
        "uz": "Bu server uchun sinxronizatsiya allaqachon navbatda",
        "ru": "Синхронизация для этого сервера уже в очереди",
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
    "user.unknown_store": {"uz": "Bunday ombor yo'q", "ru": "Такого склада нет"},
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
