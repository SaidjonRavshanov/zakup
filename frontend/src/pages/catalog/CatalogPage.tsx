import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useDeferredValue, useState, type FormEvent } from 'react'
import { CATALOG_KEY, CATALOG_TABS, catalogApi, productsQuery, storesQuery, suppliersQuery, type Store } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import {
  EmptyState,
  FormError,
  LaserButton,
  ListRow,
  MonoLabel,
  PageHeader,
  SearchPill,
  SegmentedControl,
  Skeleton,
  StatusBadge,
  TextField,
} from '@/shared/ui'

export default function CatalogPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const tab = useSearch({ from: '/shell/catalog' }).tab ?? 'products'
  const canEdit = useHasRole('buyer', 'admin')

  const addTarget = tab === 'products' ? '/catalog/products/new' : tab === 'suppliers' ? '/catalog/suppliers/new' : null

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={t.catalog.meta}
        title={t.catalog.title}
        action={
          canEdit && addTarget ? (
            <LaserButton aria-label={t.catalog.add} icon={<Plus size={16} />} onClick={() => navigate({ to: addTarget })}>
              {t.catalog.add}
            </LaserButton>
          ) : undefined
        }
      />
      <SegmentedControl
        className="-mx-4 px-4"
        segments={CATALOG_TABS.map((value) => ({ value, label: t.catalog.tabs[value] }))}
        value={tab}
        onChange={(next) => navigate({ to: '/catalog', search: { tab: next }, replace: true })}
      />
      <div className="mt-4">
        {tab === 'products' && <ProductsTab />}
        {tab === 'suppliers' && <SuppliersTab />}
        {tab === 'stores' && <StoresTab />}
      </div>
    </div>
  )
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-[76px]" />
      ))}
    </div>
  )
}

function ProductsTab() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim())
  const { data: products, isPending } = useQuery(productsQuery(query))

  return (
    <>
      <SearchPill placeholder={t.catalog.searchProducts} value={search} onChange={(e) => setSearch(e.target.value)} />
      <div className="mt-3 flex flex-col gap-2">
        {isPending ? (
          <ListSkeleton />
        ) : !products?.length ? (
          <EmptyState code="0" title={t.common.notFound} description={t.catalog.emptyProducts} />
        ) : (
          products.map((product) => (
            <ListRow
              key={product.id}
              meta={[product.category_name ?? t.catalog.product.noCategory, product.article].filter(Boolean).join(' · ')}
              title={product.name}
              subtitle={t.catalog.offersCount(product.offers_count)}
              trailing={<span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-3">{t.units[product.base_unit]}</span>}
              badge={product.from_iiko ? <StatusBadge tone="info">{t.catalog.fromIiko}</StatusBadge> : undefined}
              onClick={() => navigate({ to: '/catalog/products/$productId', params: { productId: product.id } })}
            />
          ))
        )}
      </div>
    </>
  )
}

function SuppliersTab() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim())
  const { data: suppliers, isPending } = useQuery(suppliersQuery(query))

  return (
    <>
      <SearchPill placeholder={t.catalog.searchSuppliers} value={search} onChange={(e) => setSearch(e.target.value)} />
      <div className="mt-3 flex flex-col gap-2">
        {isPending ? (
          <ListSkeleton />
        ) : !suppliers?.length ? (
          <EmptyState code="0" title={t.common.notFound} description={t.catalog.emptySuppliers} />
        ) : (
          suppliers.map((supplier) => (
            <ListRow
              key={supplier.id}
              meta={supplier.inn ? `${t.catalog.supplier.inn} ${supplier.inn}` : undefined}
              title={supplier.name}
              subtitle={
                supplier.payment_terms === 'deferred'
                  ? `${t.paymentTerms.deferred} · ${t.catalog.supplier.leadDays(supplier.deferral_days)}`
                  : t.paymentTerms[supplier.payment_terms]
              }
              badge={
                supplier.payment_methods.length ? (
                  <StatusBadge tone="info">{supplier.payment_methods.map((m) => t.paymentMethod[m]).join(' · ')}</StatusBadge>
                ) : undefined
              }
              onClick={() => navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId: supplier.id } })}
            />
          ))
        )}
      </div>
    </>
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
    <div className="flex flex-col gap-2">
      {isPending ? (
        <ListSkeleton />
      ) : !stores?.length ? (
        <EmptyState code="0" title={t.common.notFound} description={t.catalog.emptyStores} />
      ) : (
        groupByBranch(stores).map(([branch, items]) => (
          <section key={branch} className="mb-2">
            <MonoLabel className="mb-2 mt-2">{`${branch} · ${items.length}`}</MonoLabel>
            <div className="flex flex-col gap-2">
              {items.map((store) => (
                <ListRow
                  key={store.id}
                  title={store.name}
                  subtitle={store.address ?? undefined}
                  badge={store.from_iiko ? <StatusBadge tone="info">{t.catalog.fromIiko}</StatusBadge> : undefined}
                />
              ))}
            </div>
          </section>
        ))
      )}

      {isAdmin && (
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3 rounded-card border border-border-soft p-4">
          <TextField label={t.catalog.store.new} required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
          <TextField label={t.catalog.store.address} maxLength={500} value={address} onChange={(e) => setAddress(e.target.value)} />
          <FormError>{create.error && describeError(create.error, t)}</FormError>
          <LaserButton type="submit" block icon={<Plus size={16} />} loading={create.isPending} disabled={!name.trim()}>
            {t.catalog.add}
          </LaserButton>
        </form>
      )}
    </div>
  )
}
