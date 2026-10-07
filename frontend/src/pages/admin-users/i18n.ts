/** Xodim kartasi: zk'da yo'q matnlar (rol bo'yicha omborlar). */
export const L = {
  ru: {
    stores: 'Склады',
    pickStores: 'Склады для роли',
    storesN: (n: number) => `${n} ${n % 10 === 1 && n % 100 !== 11 ? 'склад' : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? 'склада' : 'складов'}`,
    done: 'Готово',
    noneHint: 'Выберите хотя бы один склад или «Все склады»',
    scopeNote: 'Роль действует только на выбранных складах: заявки, приёмка и уведомления — только по ним.',
    adminAll: 'Админ работает на всех складах',
  },
  uz: {
    stores: 'Omborlar',
    pickStores: 'Rol uchun omborlar',
    storesN: (n: number) => `${n} ta ombor`,
    done: 'Tayyor',
    noneHint: 'Kamida bitta omborni yoki «Barcha omborlar»ni tanlang',
    scopeNote: 'Rol faqat tanlangan omborlarda amal qiladi: zayavka, qabul va xabarlar — faqat ular bo‘yicha.',
    adminAll: 'Admin barcha omborlarda ishlaydi',
  },
} as const
