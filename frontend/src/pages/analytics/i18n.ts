/** Prototip lug'atida (zk.ts) yo'q qatorlar — faqat analitika sahifasi uchun. */
export const L = {
  ru: {
    hours: 'ч',
    overpay: 'переплата',
    noScore: 'нет приёмок',
    whyTitle: 'Почему такой балл',
    whyLateTitle: 'Опоздания',
    whyStart: 'Каждый поставщик начинает со 100 баллов. Баллы снимаются за проблемы на приёмках за период:',
    whyBasis: 'Основа: {receipts} и {orders} за период',
    whyShort: '{v} позиций привезли меньше допуска или не привезли',
    whyDefect: '{v} суммы приёмок ушло в брак',
    whyPrice: 'в {v} позиций цена в накладной выше заказа сверх допуска',
    whyLate: '{v} приёмок позже даты поставки',
    whyMax: 'макс. −{n}',
    whyTotal: 'Итого',
    whyScale: '80 и выше — хорошо, 60–79 — средне, ниже 60 — плохо. Скорость ответа на заказ в балл не входит.',
    whyNone: 'Приёмок за период не было — оценивать пока не по чему.',
    whyTap: 'Нажмите на поставщика — покажем, из чего сложился балл',
  },
  uz: {
    hours: 'soat',
    overpay: 'ortiqcha',
    noScore: 'qabul yo‘q',
    whyTitle: 'Nega shu ball',
    whyLateTitle: 'Kechikish',
    whyStart: 'Har bir yetkazuvchi 100 balldan boshlaydi. Davrdagi qabullardagi muammolar uchun ball ayiriladi:',
    whyBasis: 'Asos: davrda {receipts} va {orders}',
    whyShort: 'pozitsiyalarning {v} qismi dopuskdan kam keldi yoki kelmadi',
    whyDefect: 'qabul summasining {v} qismi brak',
    whyPrice: 'pozitsiyalarning {v} qismida nakladnoy narxi buyurtmadan dopuskdan ortiq',
    whyLate: 'qabullarning {v} qismi yetkazish sanasidan kech',
    whyMax: 'maks. −{n}',
    whyTotal: 'Jami',
    whyScale: '80 va undan yuqori — yaxshi, 60–79 — o‘rtacha, 60 dan past — yomon. Buyurtmaga javob tezligi ballga kirmaydi.',
    whyNone: 'Davrda qabul bo‘lmagan — hozircha baholash uchun ma’lumot yo‘q.',
    whyTap: 'Yetkazuvchini bosing — ball nimadan iboratligini ko‘rsatamiz',
  },
} as const

export const fill = (text: string, values: Record<string, string>) =>
  text.replace(/\{(\w+)\}/g, (_, key: string) => values[key] ?? '')
