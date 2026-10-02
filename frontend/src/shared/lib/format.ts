/** Til bo'yicha formatlovchilar. Komponentlar ularni `useI18n().fmt` orqali oladi (til almashsa qayta chiziladi). */

export interface CompactSuffixes {
  thousand: string
  million: string
  billion: string
}

export interface Formatters {
  /** 1250000 → "1 250 000" (so'mda tiyin ko'rsatilmaydi). */
  money(value: number): string
  /** 1250000 → "1,3 mln" / "1,3 млн" — KPI plitkalari uchun. */
  moneyCompact(value: number): string
  qty(value: number): string
  percent(value: number): string
  date(iso: string): string
  time(iso: string): string
}

export function createFormatters(intlLocale: string, compact: CompactSuffixes): Formatters {
  const moneyFmt = new Intl.NumberFormat(intlLocale, { maximumFractionDigits: 0 })
  const oneDecimal = new Intl.NumberFormat(intlLocale, { maximumFractionDigits: 1 })
  const qtyFmt = new Intl.NumberFormat(intlLocale, { maximumFractionDigits: 3 })
  const percentFmt = new Intl.NumberFormat(intlLocale, { maximumFractionDigits: 1, signDisplay: 'exceptZero' })
  const dateFmt = new Intl.DateTimeFormat(intlLocale, { day: '2-digit', month: 'short' })
  const timeFmt = new Intl.DateTimeFormat(intlLocale, { hour: '2-digit', minute: '2-digit' })
  // Intl 'compact' har xil brauzerda har xil (ru → "млн", uz → ba'zan inglizcha) — o'zimiz
  const steps = [
    { value: 1e9, suffix: compact.billion },
    { value: 1e6, suffix: compact.million },
    { value: 1e3, suffix: compact.thousand },
  ]

  return {
    money: (value) => moneyFmt.format(value),
    moneyCompact(value) {
      const step = steps.find((s) => Math.abs(value) >= s.value)
      return step ? `${oneDecimal.format(value / step.value)} ${step.suffix}` : oneDecimal.format(value)
    },
    qty: (value) => qtyFmt.format(value),
    percent: (value) => `${percentFmt.format(value)}%`,
    date: (iso) => dateFmt.format(new Date(iso)),
    time: (iso) => timeFmt.format(new Date(iso)),
  }
}

/** "10,5" va "10.5" ikkalasi ham qabul qilinadi — omborchi klaviaturasi har xil. */
export function parseDecimal(input: string): number | null {
  const normalized = input.replace(/\s/g, '').replace(',', '.')
  if (normalized === '' || !/^-?\d*\.?\d*$/.test(normalized)) return null
  const value = Number(normalized)
  return Number.isFinite(value) ? value : null
}
