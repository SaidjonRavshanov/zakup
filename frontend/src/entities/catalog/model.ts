import type { UnitCode } from '@/shared/i18n/keys'

/** Pul va miqdor backend'dan satr bo'lib keladi (Decimal, ADR-09) — hisob-kitob backend'da. */
type DecimalString = string

export type PaymentTerms = 'prepay' | 'on_delivery' | 'deferred'
export type PurchaseMode = 'auto' | 'manual' | 'disabled'

export const PAYMENT_TERMS: ReadonlyArray<PaymentTerms> = ['prepay', 'on_delivery', 'deferred']
export const PURCHASE_MODES: ReadonlyArray<PurchaseMode> = ['manual', 'auto', 'disabled']
export const BASE_UNITS: ReadonlyArray<UnitCode> = ['kg', 'g', 'l', 'ml', 'pcs']
export const PACK_UNITS: ReadonlyArray<UnitCode> = ['bag', 'box', 'pack', 'pcs', 'kg', 'g', 'l', 'ml']
export const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const

/** Katalog sahifasi bo'limlari (URL: /catalog?tab=suppliers). */
export type CatalogTab = 'products' | 'suppliers' | 'stores'
export const CATALOG_TABS: ReadonlyArray<CatalogTab> = ['products', 'suppliers', 'stores']

export interface Contacts {
  phone?: string | null
  telegram?: string | null
  email?: string | null
  person?: string | null
}

export interface SupplierListItem {
  id: string
  name: string
  inn: string | null
  payment_terms: PaymentTerms
  deferral_days: number
  credit_limit: DecimalString
  archived: boolean
}

export interface Offer {
  id: string
  supplier_id: string
  supplier_name: string
  product_id: string
  product_name: string
  base_unit: UnitCode
  supplier_sku: string | null
  supplier_product_name: string | null
  pack_unit: UnitCode
  pack_factor: DecimalString
  order_multiple: DecimalString
  price: DecimalString
  base_unit_price: DecimalString
  price_valid_from: string
  archived: boolean
}

export interface SupplierDetail {
  id: string
  name: string
  inn: string | null
  payment_terms: PaymentTerms
  deferral_days: number
  credit_limit: DecimalString
  min_order_amount: DecimalString
  lead_time_days: number
  order_weekdays: number[]
  delivery_weekdays: number[]
  order_cutoff: string | null
  contacts: Contacts
  archived: boolean
  offers: Offer[]
}

export interface SupplierInput {
  name: string
  inn: string | null
  payment_terms: PaymentTerms
  deferral_days: number
  credit_limit: string
  min_order_amount: string
  lead_time_days: number
  order_weekdays: number[]
  delivery_weekdays: number[]
  order_cutoff: string | null
  contacts: Contacts
}

export interface Store {
  id: string
  name: string
  address: string | null
  from_iiko: boolean
  archived: boolean
}

export interface Category {
  id: string
  name: string
  parent_id: string | null
  monthly_budget: DecimalString | null
}

export interface ProductListItem {
  id: string
  name: string
  article: string | null
  base_unit: UnitCode
  category_id: string | null
  category_name: string | null
  offers_count: number
  from_iiko: boolean
  archived: boolean
}

export interface PurchaseCard {
  id: string
  product_id: string
  store_id: string
  store_name: string
  mode: PurchaseMode
  safety_stock: DecimalString
  coverage_days: number
  shelf_life_days: number | null
  seasonal_factor: DecimalString
  primary_supplier_id: string | null
  primary_supplier_name: string | null
  alternative_supplier_id: string | null
  alternative_supplier_name: string | null
}

export interface ProductDetail extends Omit<ProductListItem, 'offers_count'> {
  offers: Offer[]
  cards: PurchaseCard[]
}

export interface ProductInput {
  name: string
  base_unit: UnitCode
  article: string | null
  category_id: string | null
}

export interface OfferInput {
  pack_unit: UnitCode
  pack_factor: string
  order_multiple: string
  supplier_sku: string | null
  supplier_product_name: string | null
  price: string
}

export interface PriceHistoryEntry {
  price: DecimalString
  valid_from: string
  source: 'manual' | 'iiko' | 'supplier_response' | 'receipt'
  created_at: string
}

export type PurchaseCardInput = Omit<PurchaseCard, 'id' | 'store_name' | 'primary_supplier_name' | 'alternative_supplier_name'>
