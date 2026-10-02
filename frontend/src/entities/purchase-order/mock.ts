/**
 * Vaqtinchalik ma'lumotlar — backend procurement moduli tayyor bo'lguncha.
 * Haqiqiy API ham nomlarni tanlangan tilda qaytaradi (Accept-Language), shuning uchun mock ham tilga bog'liq.
 * API ulanganda faqat api.ts dagi queryFn almashtiriladi, UI o'zgarmaydi.
 */
import type { Locale } from '@/shared/i18n'
import { orderTotal, type PurchaseOrder, type PurchaseOrderLine } from './model'

type Text = Record<Locale, string>

const day = (offset: number) => {
  const date = new Date()
  date.setDate(date.getDate() + offset)
  return date.toISOString().slice(0, 10)
}

const STORES = {
  kitchen: { uz: 'Oshxona', ru: 'Кухня' },
  bar: { uz: 'Bar', ru: 'Бар' },
} satisfies Record<string, Text>

const SUPPLIERS = {
  dairy: { uz: 'Sutli Vodiy MChJ', ru: 'ООО «Сутли Водий»' },
  meat: { uz: 'Meat Pro', ru: 'Meat Pro' },
  farm: { uz: 'Green Farm', ru: 'Green Farm' },
  bar: { uz: 'Bar Supply', ru: 'Bar Supply' },
} satisfies Record<string, Text>

interface LineSeed extends Omit<PurchaseOrderLine, 'productName'> {
  productName: Text
}

const DAIRY: LineSeed[] = [
  { id: 'l1', productName: { uz: 'Sut 3,2%', ru: 'Молоко 3,2%' }, unit: 'l', qtyOrdered: 40, priceOrdered: 12_500 },
  { id: 'l2', productName: { uz: 'Qaymoq 20%', ru: 'Сливки 20%' }, unit: 'kg', qtyOrdered: 8, priceOrdered: 38_000 },
  { id: 'l3', productName: { uz: 'Pishloq Motsarella', ru: 'Сыр Моцарелла' }, unit: 'kg', qtyOrdered: 12, priceOrdered: 96_000 },
]

const MEAT: LineSeed[] = [
  { id: 'l4', productName: { uz: "Mol go'shti (lahm)", ru: 'Говядина (мякоть)' }, unit: 'kg', qtyOrdered: 25, priceOrdered: 118_000 },
  { id: 'l5', productName: { uz: 'Tovuq filesi', ru: 'Куриное филе' }, unit: 'kg', qtyOrdered: 30, priceOrdered: 54_000 },
]

const VEG: LineSeed[] = [
  { id: 'l6', productName: { uz: 'Pomidor', ru: 'Помидоры' }, unit: 'kg', qtyOrdered: 20, priceOrdered: 16_000 },
  { id: 'l7', productName: { uz: 'Bodring', ru: 'Огурцы' }, unit: 'kg', qtyOrdered: 15, priceOrdered: 11_000 },
  { id: 'l8', productName: { uz: 'Kartoshka', ru: 'Картофель' }, unit: 'kg', qtyOrdered: 50, priceOrdered: 6_500 },
  { id: 'l9', productName: { uz: 'Piyoz', ru: 'Лук' }, unit: 'kg', qtyOrdered: 25, priceOrdered: 5_000 },
  { id: 'l10', productName: { uz: 'Tuxum', ru: 'Яйца' }, unit: 'pcs', qtyOrdered: 360, priceOrdered: 1_400 },
]

interface OrderSeed extends Omit<PurchaseOrder, 'totalAmount' | 'lines' | 'supplierName' | 'storeName'> {
  supplier: keyof typeof SUPPLIERS
  store: keyof typeof STORES
  lines: LineSeed[]
}

const SEEDS: OrderSeed[] = [
  { id: 'po-1042', number: 'PO-1042', supplier: 'dairy', store: 'kitchen', status: 'CONFIRMED', deliveryDate: day(0), lines: DAIRY },
  { id: 'po-1041', number: 'PO-1041', supplier: 'meat', store: 'kitchen', status: 'RECEIVING', deliveryDate: day(0), lines: MEAT },
  { id: 'po-1040', number: 'PO-1040', supplier: 'farm', store: 'kitchen', status: 'SENT', deliveryDate: day(1), lines: VEG },
  { id: 'po-1039', number: 'PO-1039', supplier: 'bar', store: 'bar', status: 'REAPPROVAL', deliveryDate: day(1), lines: DAIRY.slice(0, 1) },
  { id: 'po-1038', number: 'PO-1038', supplier: 'meat', store: 'kitchen', status: 'PARTIALLY_RECEIVED', deliveryDate: day(-1), lines: MEAT },
  { id: 'po-1037', number: 'PO-1037', supplier: 'farm', store: 'kitchen', status: 'CLOSED', deliveryDate: day(-2), lines: VEG },
  { id: 'po-1036', number: 'PO-1036', supplier: 'dairy', store: 'bar', status: 'CANCELLED', deliveryDate: day(-3), lines: DAIRY.slice(1) },
]

export function buildMockOrders(locale: Locale): PurchaseOrder[] {
  return SEEDS.map(({ supplier, store, lines, ...seed }) => {
    const localizedLines = lines.map((line) => ({ ...line, productName: line.productName[locale] }))
    return {
      ...seed,
      supplierName: SUPPLIERS[supplier][locale],
      storeName: STORES[store][locale],
      lines: localizedLines,
      totalAmount: orderTotal(localizedLines),
    }
  })
}
