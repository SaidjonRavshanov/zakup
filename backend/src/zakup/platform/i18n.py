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
    # --- procurement: zayavka
    "invalid_request": {"uz": "Zayavka ma'lumotlari noto'g'ri", "ru": "Некорректные данные заявки"},
    "request.not_found": {"uz": "Zayavka topilmadi", "ru": "Заявка не найдена"},
    "request.modified": {
        "uz": "Zayavka boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Заявка изменена другим пользователем",
    },
    "request.invalid_status": {
        "uz": "Zayavka holatida ({status}) bu amalni bajarib bo'lmaydi",
        "ru": "В статусе заявки ({status}) это действие недоступно",
    },
    "request.auto_is_system": {
        "uz": "Avto-zayavkani tizim yaratadi",
        "ru": "Авто-заявку формирует система",
    },
    "request.duplicate_product": {
        "uz": "Bu tovar zayavkada allaqachon bor — miqdorini o'zgartiring",
        "ru": "Этот товар уже есть в заявке — измените количество",
    },
    "request.too_many_lines": {"uz": "Pozitsiyalar {max} tadan oshmasin", "ru": "Не больше {max} позиций"},
    "request.qty_positive": {"uz": "Miqdor 0 dan katta bo'lishi kerak", "ru": "Количество должно быть больше 0"},
    "request.needed_by_past": {
        "uz": "\"Kerak bo'lgan sana\" o'tgan kun bo'lmasin",
        "ru": "Дата «нужно к» не может быть в прошлом",
    },
    "request.empty": {"uz": "Zayavkada pozitsiya yo'q", "ru": "В заявке нет позиций"},
    "request.line_not_found": {"uz": "Pozitsiya topilmadi", "ru": "Позиция не найдена"},
    "request.line_without_supplier": {
        "uz": "Barcha tasdiqlanadigan pozitsiyalarga yetkazuvchi tanlang",
        "ru": "Выберите поставщика для всех утверждаемых позиций",
    },
    "request.nothing_approved": {"uz": "Tasdiqlash uchun pozitsiya tanlanmagan", "ru": "Не выбраны позиции"},
    "request.comment_required": {"uz": "Izoh yozing", "ru": "Напишите комментарий"},
    "request.offer_mismatch": {
        "uz": "Bu taklif shu tovar uchun emas yoki arxivda",
        "ru": "Предложение не для этого товара или в архиве",
    },
    "request.offer_unavailable": {
        "uz": "Yetkazuvchi taklifi arxivga o'tgan — boshqa yetkazuvchini tanlang",
        "ru": "Предложение поставщика в архиве — выберите другого поставщика",
    },
    "approval_limit": {"uz": "Tasdiqlash limiti yetarli emas", "ru": "Недостаточно лимита утверждения"},
    "approval.no_role": {
        "uz": "Bu ombor bo'yicha tasdiqlash huquqingiz yo'q",
        "ru": "Нет права утверждать по этому складу",
    },
    "approval.over_limit": {
        "uz": "Summa {amount} limitingizdan ({limit}) oshadi — yuqori tasdiqlovchi kerak",
        "ru": "Сумма {amount} выше вашего лимита ({limit}) — нужен утверждающий выше",
    },
    # --- procurement: buyurtma
    "invalid_order": {"uz": "Buyurtma ma'lumotlari noto'g'ri", "ru": "Некорректные данные заказа"},
    "order.not_found": {"uz": "Buyurtma topilmadi", "ru": "Заказ не найден"},
    "order.modified": {
        "uz": "Buyurtma boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Заказ изменён другим пользователем",
    },
    "order.invalid_status": {
        "uz": "Buyurtma holatida ({status}) bu amalni bajarib bo'lmaydi",
        "ru": "В статусе заказа ({status}) это действие недоступно",
    },
    "order.empty": {"uz": "Buyurtmada pozitsiya yo'q", "ru": "В заказе нет позиций"},
    "order.line_not_found": {"uz": "Buyurtma pozitsiyasi topilmadi", "ru": "Позиция заказа не найдена"},
    "order.qty_required": {"uz": "Yangi miqdorni kiriting", "ru": "Укажите новое количество"},
    "order.price_required": {"uz": "Yangi narxni kiriting", "ru": "Укажите новую цену"},
    "order.reason_required": {"uz": "Bekor qilish sababini yozing", "ru": "Укажите причину отмены"},
    "order.link_invalid": {
        "uz": "Havola yaroqsiz yoki muddati o'tgan",
        "ru": "Ссылка недействительна или устарела",
    },
    "order.not_receivable": {
        "uz": "Bu buyurtmani hozir qabul qilib bo'lmaydi (holati: {status})",
        "ru": "Этот заказ сейчас нельзя принять (статус: {status})",
    },
    # --- receiving
    "invalid_receipt": {"uz": "Qabul ma'lumotlari noto'g'ri", "ru": "Некорректные данные приёмки"},
    "receipt.not_found": {"uz": "Qabul topilmadi", "ru": "Приёмка не найдена"},
    "receipt.modified": {
        "uz": "Qabul boshqa foydalanuvchi tomonidan o'zgartirilgan",
        "ru": "Приёмка изменена другим пользователем",
    },
    "receipt.id_reused": {
        "uz": "Bu qabul ID'si boshqa buyurtma uchun ishlatilgan",
        "ru": "Этот ID приёмки уже использован для другого заказа",
    },
    "receipt.order_already_received": {"uz": "Bu buyurtma allaqachon qabul qilingan", "ru": "Этот заказ уже принят"},
    "receipt.photo_required": {
        "uz": "Nakladnoy fotosisiz qabulni yakunlab bo'lmaydi",
        "ru": "Без фото накладной приёмку завершить нельзя",
    },
    "receipt.payment_method_required": {
        "uz": "Joyida to'langan bo'lsa — to'lov usulini tanlang (naqd yoki o'tkazma)",
        "ru": "Если оплачено на месте — выберите способ оплаты (наличные или перечисление)",
    },
    "receipt.unknown_line": {"uz": "Buyurtmada bunday pozitsiya yo'q", "ru": "В заказе нет такой позиции"},
    "receipt.negative": {
        "uz": "Miqdor va narx manfiy bo'lmasin",
        "ru": "Количество и цена не могут быть отрицательными",
    },
    "receipt.defect_range": {
        "uz": "Brak miqdori 0 dan qabul qilingan miqdorgacha",
        "ru": "Брак — от 0 до принятого количества",
    },
    "receipt.defect_reason_required": {"uz": "Brak sababini yozing", "ru": "Укажите причину брака"},
    "receipt.no_open_dispute": {"uz": "Ochiq nizo yo'q", "ru": "Нет открытого спора"},
    "receipt.comment_required": {"uz": "Izoh yozing", "ru": "Напишите комментарий"},
    "receipt.file_type": {
        "uz": "Faqat rasm (JPEG, PNG, WebP) yoki PDF",
        "ru": "Только изображение (JPEG, PNG, WebP) или PDF",
    },
    "receipt.file_size": {"uz": "Fayl {max_mb} MB dan oshmasin", "ru": "Файл не больше {max_mb} МБ"},
    "receipt.file_not_found": {"uz": "Fayl topilmadi", "ru": "Файл не найден"},
    # --- iiko kirimi
    "iiko_mapping": {"uz": "iiko'da mos ma'lumot topilmadi", "ru": "В iiko не найдено соответствие"},
    "iiko.receipt_not_ready": {"uz": "Qabul eksportga tayyor emas", "ru": "Приёмка не готова к выгрузке"},
    "iiko.no_server_for_store": {
        "uz": "Ombor filiali uchun iiko serveri sozlanmagan",
        "ru": "Для филиала склада не настроен сервер iiko",
    },
    "iiko.store_not_linked": {
        "uz": "Ombor iiko bilan bog'lanmagan — ma'lumotnomani sinxronlang",
        "ru": "Склад не связан с iiko — синхронизируйте справочники",
    },
    "iiko.product_not_linked": {
        "uz": "Tovar iiko'da topilmadi — ma'lumotnomani sinxronlang",
        "ru": "Товар не найден в iiko — синхронизируйте справочники",
    },
    "iiko.supplier_not_linked": {
        "uz": "Yetkazuvchi iiko'da topilmadi — ma'lumotnomani sinxronlang",
        "ru": "Поставщик не найден в iiko — синхронизируйте справочники",
    },
    "iiko.import_rejected": {"uz": "iiko nakladnoyni qabul qilmadi: {error}", "ru": "iiko отклонил накладную: {error}"},
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
    "offer.price_future": {
        "uz": "Narx kelajakdagi sanadan kiritilmaydi — sana bugun yoki o'tgan kun bo'lsin",
        "ru": "Нельзя ввести цену с будущей даты — укажите сегодня или прошедший день",
    },
    "user.admin_must_be_global": {
        "uz": "Admin roli faqat barcha omborlarga beriladi",
        "ru": "Роль админа выдаётся только на все склады",
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
    # ---- analytics
    "invalid_report": {"uz": "Hisobot parametrlari noto'g'ri", "ru": "Некорректные параметры отчёта"},
    "analytics.period_range": {
        "uz": "Davr noto'g'ri: boshlanishi tugashidan oldin va {max} kundan oshmasin",
        "ru": "Некорректный период: начало раньше конца и не длиннее {max} дней",
    },
    # ---- finance (to'lovlar)
    "invalid_payment": {"uz": "To'lov ma'lumotlari noto'g'ri", "ru": "Некорректные данные оплаты"},
    "payment.not_found": {"uz": "To'lov zayavkasi topilmadi", "ru": "Заявка на оплату не найдена"},
    "payment.modified": {
        "uz": "Ma'lumot boshqa foydalanuvchi tomonidan o'zgartirilgan — sahifani yangilang",
        "ru": "Данные изменены другим пользователем — обновите страницу",
    },
    "payment.invalid_status": {
        "uz": "Zayavkaning hozirgi holatida bu amal mumkin emas",
        "ru": "В текущем статусе заявки это действие недоступно",
    },
    "payment.no_lines": {"uz": "Kamida bitta nakladnoy tanlang", "ru": "Выберите хотя бы одну накладную"},
    "payment.duplicate_line": {
        "uz": "Bitta nakladnoy ikki marta tanlangan",
        "ru": "Одна накладная выбрана дважды",
    },
    "payment.amount_invalid": {"uz": "Summa noto'g'ri", "ru": "Некорректная сумма"},
    "payment.amount_below_paid": {
        "uz": "Yakuniy summa allaqachon to'langanidan kam",
        "ru": "Итоговая сумма меньше уже оплаченной",
    },
    "payment.obligation_not_found": {
        "uz": "Nakladnoy bu yetkazuvchiga tegishli emas yoki topilmadi",
        "ru": "Накладная не найдена или относится к другому поставщику",
    },
    "payment.obligation_blocked": {
        "uz": "{number}: nizo ochiq — nizo yopilmaguncha to'lab bo'lmaydi",
        "ru": "{number}: открыт спор — до его закрытия оплата заблокирована",
    },
    "payment.over_outstanding": {
        "uz": "{number}: summa qarz qoldig'idan (boshqa zayavkalardagini hisobga olib) katta",
        "ru": "{number}: сумма больше остатка долга (с учётом других заявок)",
    },
    "payment.comment_required": {"uz": "Sababini yozing", "ru": "Укажите причину"},
    "payment.proof_not_found": {"uz": "To'lov tasdig'i fayli topilmadi", "ru": "Файл подтверждения оплаты не найден"},
    "payment.file_type": {
        "uz": "Faqat rasm (JPEG, PNG, WebP) yoki PDF",
        "ru": "Только изображение (JPEG, PNG, WebP) или PDF",
    },
    "payment.file_size": {"uz": "Fayl {max_mb} MB dan katta", "ru": "Файл больше {max_mb} МБ"},
    "payment.file_not_found": {"uz": "Fayl topilmadi", "ru": "Файл не найден"},
    "approval.supplier_overdue": {
        "uz": "{supplier}: muddati o'tgan qarz bor — buyurtmani faqat admin tasdiqlaydi",
        "ru": "{supplier}: есть просроченный долг — заказ утверждает только администратор",
    },
    "approval.supplier_over_limit": {
        "uz": "{supplier}: kredit limiti yetmaydi — buyurtmani faqat admin tasdiqlaydi",
        "ru": "{supplier}: кредитный лимит исчерпан — заказ утверждает только администратор",
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
