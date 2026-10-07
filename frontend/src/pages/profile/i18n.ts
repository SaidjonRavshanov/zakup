/** Profil: zk'da yo'q matnlar (chiqishda navbat ogohlantirishi). */
export const L = {
  ru: {
    queueTitle: (n: number) => `Не отправлено приёмок: ${n}. Выйти?`,
    queueBody: 'Неотправленные приёмки будут удалены с этого устройства и не попадут на сервер.',
  },
  uz: {
    queueTitle: (n: number) => `Yuborilmagan qabullar: ${n}. Chiqasizmi?`,
    queueBody: "Yuborilmagan qabullar bu qurilmadan o'chiriladi va serverga yetib bormaydi.",
  },
} as const
