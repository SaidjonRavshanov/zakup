import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type {
  Category,
  OfferInput,
  PriceHistoryEntry,
  ProductDetail,
  ProductInput,
  ProductListItem,
  PurchaseCardInput,
  Store,
  SupplierDetail,
  SupplierInput,
  SupplierListItem,
} from './model'

const BASE = '/catalog'

interface Created {
  id: string
}

const query = (params: Record<string, string | boolean | undefined>) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== '') search.set(key, String(value))
  const text = search.toString()
  return text ? `?${text}` : ''
}

/** Barcha catalog so'rovlari shu kalit ostida — yozishdan keyin bitta invalidate yetadi. */
export const CATALOG_KEY = ['catalog'] as const

export const suppliersQuery = (search = '', includeArchived = false) =>
  queryOptions({
    queryKey: [...CATALOG_KEY, 'suppliers', search, includeArchived],
    queryFn: ({ signal }) =>
      apiRequest<SupplierListItem[]>(`${BASE}/suppliers${query({ search, include_archived: includeArchived || undefined, limit: '200' })}`, { signal }),
  })

export const supplierQuery = (id: string) =>
  queryOptions({
    queryKey: [...CATALOG_KEY, 'supplier', id],
    queryFn: ({ signal }) => apiRequest<SupplierDetail>(`${BASE}/suppliers/${id}`, { signal }),
  })

export const productsQuery = (search = '', categoryId = '') =>
  queryOptions({
    queryKey: [...CATALOG_KEY, 'products', search, categoryId],
    queryFn: ({ signal }) =>
      apiRequest<ProductListItem[]>(`${BASE}/products${query({ search, category_id: categoryId, limit: '200' })}`, { signal }),
  })

export const productQuery = (id: string) =>
  queryOptions({
    queryKey: [...CATALOG_KEY, 'product', id],
    queryFn: ({ signal }) => apiRequest<ProductDetail>(`${BASE}/products/${id}`, { signal }),
  })

export const storesQuery = queryOptions({
  queryKey: [...CATALOG_KEY, 'stores'],
  queryFn: ({ signal }) => apiRequest<Store[]>(`${BASE}/stores`, { signal }),
  staleTime: 5 * 60_000,
})

export const categoriesQuery = queryOptions({
  queryKey: [...CATALOG_KEY, 'categories'],
  queryFn: ({ signal }) => apiRequest<Category[]>(`${BASE}/categories`, { signal }),
  staleTime: 5 * 60_000,
})

export const priceHistoryQuery = (offerId: string) =>
  queryOptions({
    queryKey: [...CATALOG_KEY, 'price-history', offerId],
    queryFn: ({ signal }) => apiRequest<PriceHistoryEntry[]>(`${BASE}/offers/${offerId}/price-history`, { signal }),
  })

export const catalogApi = {
  createSupplier: (body: SupplierInput) => apiRequest<Created>(`${BASE}/suppliers`, { method: 'POST', body }),
  updateSupplier: (id: string, body: SupplierInput) => apiRequest<void>(`${BASE}/suppliers/${id}`, { method: 'PUT', body }),
  archiveSupplier: (id: string) => apiRequest<void>(`${BASE}/suppliers/${id}/archive`, { method: 'POST' }),

  createProduct: (body: ProductInput) => apiRequest<Created>(`${BASE}/products`, { method: 'POST', body }),
  updateProduct: (id: string, body: ProductInput) => apiRequest<void>(`${BASE}/products/${id}`, { method: 'PUT', body }),
  archiveProduct: (id: string) => apiRequest<void>(`${BASE}/products/${id}/archive`, { method: 'POST' }),

  createStore: (body: { name: string; address: string | null }) => apiRequest<Created>(`${BASE}/stores`, { method: 'POST', body }),
  createCategory: (body: { name: string }) => apiRequest<Created>(`${BASE}/categories`, { method: 'POST', body }),

  addOffer: (supplierId: string, body: OfferInput & { product_id: string }) =>
    apiRequest<Created>(`${BASE}/suppliers/${supplierId}/offers`, { method: 'POST', body }),
  updateOffer: (id: string, body: OfferInput & { price_valid_from?: string | null }) =>
    apiRequest<void>(`${BASE}/offers/${id}`, { method: 'PUT', body }),
  archiveOffer: (id: string) => apiRequest<void>(`${BASE}/offers/${id}/archive`, { method: 'POST' }),

  configureCard: (body: PurchaseCardInput) => apiRequest<Created>(`${BASE}/purchase-cards`, { method: 'PUT', body }),
}
