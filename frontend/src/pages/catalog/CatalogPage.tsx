/** Katalog (prototip "catalog", vmCatalog): bo'limlar (tovarlar / yetkazib beruvchilar / omborlar), qidiruv, qatorlar. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useDeferredValue, useState, type FormEvent } from 'react'
import {
  CATALOG_KEY,
  CATALOG_TABS,
  catalogApi,
  productsQuery,
  storesQuery,
  suppliersQuery,
  type CatalogTab,
  type Store,
} from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Btn, Empty, Field, Input, PageHead, Row, RowsSkeleton, SearchInput, Section, Seg, Tag } from '@/shared/kit'
import { methodsLabel, termsLabel } from './format'

export default function CatalogPage() {
  const { z } = useZk()
  const navigate = useNavigate()
  const tab = useSearch({ from: '/shell/catalog' }).tab ?? 'products'
  const canEdit = useHasRole('buyer', 'admin')
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim())

  // Bo'lim sonlari — filtrsiz ro'yxatlardan (kesh bilan)
  const { data: allProducts } = useQuery(productsQuery())
  const { data: allSuppliers } = useQuery(suppliersQuery())
  const { data: stores } = useQuery(storesQuery)
  const counts: Record<CatalogTab, number | undefined> = {
    products: allProducts?.length,
    suppliers: allSuppliers?.length,
    stores: stores?.length,
  }
  const labels: Record<CatalogTab, string> = { products: z.c_products, suppliers: z.c_suppliers, stores: z.c_stores }

  const addTarget = tab === 'products' ? '/catalog/products/new' : tab === 'suppliers' ? '/catalog/suppliers/new' : null

  return (
    <div className="mx-auto w-full max-w-[1040px]">
      <PageHead
        title={z.catalog}
        aside={
          canEdit && addTarget ? (
            <Btn icon={<Plus size={20} />} onClick={() => navigate({ to: addTarget })}>
              {z.a_add}
            </Btn>
          ) : undefined
        }
      />
      <Seg
        className="mt-3"
        options={CATALOG_TABS.map((value) => ({ value, label: labels[value], count: counts[value] }))}
        value={tab}
        onChange={(next) => {
          setSearch('')
          void navigate({ to: '/catalog', search: { tab: next }, replace: true })
        }}
      />
      {tab !== 'stores' && (
        <SearchInput
          className="mt-3"
          value={search}
          onChange={setSearch}
          placeholder={tab === 'suppliers' ? z.search_sup : z.search_prod}
        />
      )}
      {tab === 'products' && <ProductsTab query={query} />}
      {tab === 'suppliers' && <SuppliersTab query={query} />}
      {tab === 'stores' && <StoresTab />}
    </div>
  )
}

function ProductsTab({ query }: { query: string }) {
  const { t } = useI18n()
  const { z, f } = useZk()
  const navigate = useNavigate()
  const { data: products, isPending } = useQuery(productsQuery(query))

  if (isPending) return <RowsSkeleton n={5} />
  if (!products?.length) return <Empty title={z.nothing_found} hint={t.catalog.emptyProducts} />
  return (
    <div>
      {products.map((product) => (
        <Row
          key={product.id}
          meta={[product.category_name ?? t.catalog.product.noCategory, product.article].filter(Boolean).join(' · ')}
          title={product.name}
          sub={`${z.suppliers_n}: ${product.offers_count} · ${f.unit(product.base_unit)}`}
          badge={product.from_iiko ? <Tag tone="ok">iiko</Tag> : <Tag>{z.manual}</Tag>}
          onClick={() => navigate({ to: '/catalog/products/$productId', params: { productId: product.id } })}
        />
      ))}
    </div>
  )
}

function SuppliersTab({ query }: { query: string }) {
  const { t } = useI18n()
  const { z } = useZk()
  const navigate = useNavigate()
  const { data: suppliers, isPending } = useQuery(suppliersQuery(query))

  if (isPending) return <RowsSkeleton n={5} />
  if (!suppliers?.length) return <Empty title={z.nothing_found} hint={t.catalog.emptySuppliers} />
  return (
    <div>
      {suppliers.map((supplier) => (
        <Row
          key={supplier.id}
          meta={supplier.inn ? `${z.inn} ${supplier.inn}` : undefined}
          title={supplier.name}
          sub={termsLabel(z, supplier.payment_terms, supplier.deferral_days)}
          badge={supplier.payment_methods.length ? <Tag>{methodsLabel(z, supplier.payment_methods, ' / ')}</Tag> : undefined}
          onClick={() => navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId: supplier.id } })}
        />
      ))}
    </div>
  )
}

/** Filial tartibi backend'dan keladi (bo'lim kodi bo'yicha); filialsiz — "—". */
function groupByBranch(stores: Store[]): Array<[string, Store[]]> {
  const groups = new Map<string, Store[]>()
  for (const store of stores) {
    const key = store.branch_name ?? '—'
    groups.set(key, [...(groups.get(key) ?? []), store])
  }
  return [...groups.entries()]
}

function StoresTab() {
  const { t } = useI18n()
  const { z } = useZk()
  const queryClient = useQueryClient()
  const isAdmin = useHasRole('admin')
  const { data: stores, isPending } = useQuery(storesQuery)
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const create = useMutation({
    mutationFn: () => catalogApi.createStore({ name: name.trim(), address: address.trim() || null }),
    onSuccess: () => {
      setName('')
      setAddress('')
      return queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
    },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate()
  }

  return (
    <>
      {isPending ? (
        <div className="mt-3">
          <RowsSkeleton n={4} />
        </div>
      ) : !stores?.length ? (
        <Empty title={z.nothing_found} hint={t.catalog.emptyStores} />
      ) : (
        groupByBranch(stores).map(([branch, items]) => (
          <section key={branch}>
            <Section className="mt-5">{branch}</Section>
            {items.map((store) => (
              <div key={store.id} className="flex min-h-[52px] items-center justify-between gap-3 border-b border-line py-2">
                <div className="min-w-0">
                  <div className="text-[16px]">{store.name}</div>
                  {store.address && <div className="text-[13px] text-n7">{store.address}</div>}
                </div>
                <span className="shrink-0 text-[13px] text-n7">{store.from_iiko ? `iiko · ${branch}` : z.manual}</span>
              </div>
            ))}
          </section>
        ))
      )}

      {isAdmin && (
        <form onSubmit={submit} className="mt-6 flex flex-col gap-3 border border-line p-3">
          <Field label={t.catalog.store.new}>
            <Input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t.catalog.store.address} error={create.error ? describeError(create.error, t) : undefined}>
            <Input maxLength={500} value={address} onChange={(e) => setAddress(e.target.value)} />
          </Field>
          <Btn type="submit" block icon={<Plus size={20} />} loading={create.isPending} disabled={!name.trim()}>
            {z.a_add}
          </Btn>
        </form>
      )}
    </>
  )
}
