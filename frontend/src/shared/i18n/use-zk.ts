/**
 * Yangi dizayn lug'ati va formatlash — prototip (Zakup Prototype.dc.html) qoidalari bo'yicha:
 * pul "262 000 сум", qisqa "184,2 млн" / "975 тыс.", sana "Сегодня" / "Завтра" / "4 окт", foiz "+6,1%".
 */
import { useI18n, type Locale } from './index'
import { zkRu, zkUz, type Zk, type ZkKey } from './zk'

const NBSP = ' '
const DICT: Record<Locale, Zk> = { ru: zkRu, uz: zkUz }

/** "{id} bekor qilinsinmi?" + {id: 'Z-1'} → matn. */
export function fill(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => (key in vars ? String(vars[key]) : match))
}

const UNIT_KEY: Record<string, ZkKey> = { kg: 'u_kg', g: 'u_g', l: 'u_l', ml: 'u_ml', pcs: 'u_pc', pc: 'u_pc' }
const PACK_KEY: Record<string, ZkKey> = { bag: 'pk_bag', box: 'pk_box', pack: 'pk_pack', can: 'pk_can', tray: 'pk_tray' }

/**
 * Ruscha ko'plik: 1 задача, 2 задачи, 5 задач (one / few / many). O'zbekchada son bilan so'z o'zgarmaydi.
 * `forms` — [one, few, many].
 */
export function plural(locale: Locale, n: number, forms: readonly [string, string, string], uz: string): string {
  if (locale === 'uz') return uz
  const a = Math.abs(n) % 100
  const b = a % 10
  if (!Number.isInteger(n)) return forms[1]
  if (a >= 11 && a <= 14) return forms[2]
  if (b === 1) return forms[0]
  if (b >= 2 && b <= 4) return forms[1]
  return forms[2]
}

/** Lug'atdagi "N ta ..." so'zlarining ruscha shakllari (zk.ts da faqat "many" shakli bor). */
const RU_FORMS: Partial<Record<ZkKey, readonly [string, string, string]>> = {
  tasks_n: ['задача', 'задачи', 'задач'],
  receipts_n: ['приёмка', 'приёмки', 'приёмок'],
  drafts_n: ['черновик', 'черновика', 'черновиков'],
  orders_n: ['заказ', 'заказа', 'заказов'],
  auto_lines: ['позиция', 'позиции', 'позиций'],
}

/** Toshkent bo'yicha bugungi sana (ISO). */
export function todayIso(offsetDays = 0): string {
  const now = new Date(Date.now() + 5 * 3600_000 + offsetDays * 86_400_000)
  return now.toISOString().slice(0, 10)
}

export interface ZkFormat {
  /** 1234.5 → "1 234,5" (2 kasrgacha). */
  n(value: number, digits?: number): string
  money(value: number | string): string
  /** Qisqa: ≥1 mln → "184,2 млн", ≥10 ming → "975 тыс.", aks holda to'liq son. */
  cmp(value: number | string): string
  unit(code: string): string
  pack(code: string): string
  /** 12.5 + kg → "12,5 кг". */
  qty(value: number | string, unit: string): string
  /** ISO sana/vaqt → "Сегодня" / "Завтра" / "4 окт". */
  dt(iso: string | null | undefined): string
  /** ISO vaqt → "4 окт, 14:20". */
  dtTime(iso: string | null | undefined): string
  time(iso: string): string
  pct(value: number | string): string
  /** Son + to'g'ri shakl: cnt(3, 'tasks_n') → "3 задачи" / "3 vazifa". */
  cnt(value: number, key: ZkKey): string
}

function createZkFormat(locale: Locale, z: Zk): ZkFormat {
  const intl = locale === 'ru' ? 'ru-RU' : 'uz-Latn-UZ'
  const num = (digits: number) => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits })
  const n = (value: number, digits = 2) => num(digits).format(value).replace(/[  \s]/g, NBSP)
  const months = z.mon.split(',')
  const timeFmt = new Intl.DateTimeFormat(intl, { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Tashkent' })
  const dayOf = (iso: string) => {
    // ISO sana (YYYY-MM-DD) — o'zi; vaqt bo'lsa — Toshkent sanasi
    if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso
    return new Date(new Date(iso).getTime() + 5 * 3600_000).toISOString().slice(0, 10)
  }
  const dt = (iso: string | null | undefined) => {
    if (!iso) return '—'
    const day = dayOf(iso)
    if (day === todayIso()) return z.today_l
    if (day === todayIso(1)) return z.tomorrow_l
    const [, m, d] = day.split('-').map(Number)
    const mon = months.at((m ?? 1) - 1) ?? ''
    return locale === 'uz' ? `${d}-${mon}` : `${d} ${mon}`
  }
  const unit = (code: string) => (UNIT_KEY[code] ? z[UNIT_KEY[code]] : code)
  return {
    n,
    money: (value) => `${n(Math.round(Number(value)), 0)}${NBSP}${z.sum}`,
    cmp(value) {
      const x = Number(value)
      const a = Math.abs(x)
      if (a >= 1e6) return `${n(Math.round(x / 1e5) / 10, 1)}${NBSP}${z.mln}`
      if (a >= 1e4) return `${n(Math.round(x / 1e3), 0)}${NBSP}${z.th}`
      return n(x)
    },
    unit,
    pack: (code) => (PACK_KEY[code] ? z[PACK_KEY[code]] : unit(code)),
    qty: (value, code) => `${n(Number(value))}${NBSP}${unit(code)}`,
    dt,
    dtTime: (iso) => (iso ? `${dt(iso)}, ${timeFmt.format(new Date(iso))}` : '—'),
    time: (iso) => timeFmt.format(new Date(iso)),
    pct: (value) => {
      const x = Number(value)
      return `${x > 0 ? '+' : ''}${n(x, 1)}%`
    },
    cnt: (value, key) => {
      const forms = RU_FORMS[key]
      return `${n(value, 0)}${NBSP}${forms ? plural(locale, value, forms, z[key]) : z[key]}`
    },
  }
}

const CACHE = new Map<Locale, { z: Zk; f: ZkFormat }>()

export function useZk(): { z: Zk; f: ZkFormat; locale: Locale } {
  const { locale } = useI18n()
  let entry = CACHE.get(locale)
  if (!entry) {
    entry = { z: DICT[locale], f: createZkFormat(locale, DICT[locale]) }
    CACHE.set(locale, entry)
  }
  return { ...entry, locale }
}

export type { Zk, ZkKey }
