import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Archive, Plus, Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { BASE_UNITS, CATALOG_KEY, catalogApi, categoriesQuery, productQuery, type ProductDetail, type ProductInput } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import { telegram } from '@/shared/lib/telegram'
import { EmptyState, FormError, LaserButton, PageHeader, SelectField, Skeleton, TextField } from '@/shared/ui'

/** /catalog/products/new va /catalog/products/$productId/edit */
export default function ProductFormPage() {
  const params = useParams({ strict: false })
  const productId = params.productId
  const { data: product, isPending } = useQuery({ ...productQuery(productId ?? ''), enabled: Boolean(productId) })

  if (productId && isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (productId && !product) return <EmptyState code="404" title="404" />
  return <ProductForm product={product} />
}

function ProductForm({ product }: { product?: ProductDetail }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isAdmin = useHasRole('admin')
  const { data: categories = [] } = useQuery(categoriesQuery)
  const [form, setForm] = useState<ProductInput>({
    name: product?.name ?? '',
    base_unit: product?.base_unit ?? 'kg',
    article: product?.article ?? '',
    category_id: product?.category_id ?? null,
  })
  const [newCategory, setNewCategory] = useState('')

  const back = () =>
    product
      ? navigate({ to: '/catalog/products/$productId', params: { productId: product.id } })
      : navigate({ to: '/catalog', search: { tab: 'products' } })
  useEffect(() => telegram.backButton(back))

  const done = async (id: string) => {
    telegram.haptic.notify('success')
    await queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
    void navigate({ to: '/catalog/products/$productId', params: { productId: id }, replace: true })
  }
  const save = useMutation({
    mutationFn: async () => {
      const body = { ...form, name: form.name.trim(), article: form.article?.trim() || null }
      if (!product) return (await catalogApi.createProduct(body)).id
      await catalogApi.updateProduct(product.id, body)
      return product.id
    },
    onSuccess: done,
  })
  const archive = useMutation({
    mutationFn: () => catalogApi.archiveProduct(product!.id),
    onSuccess: () => done(product!.id),
  })
  const addCategory = useMutation({
    mutationFn: () => catalogApi.createCategory({ name: newCategory.trim() }),
    onSuccess: async ({ id }) => {
      await queryClient.invalidateQueries({ queryKey: categoriesQuery.queryKey })
      setForm((f) => ({ ...f, category_id: id }))
      setNewCategory('')
    },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }
  const failure = save.error ?? archive.error ?? addCategory.error

  return (
    <form onSubmit={submit} className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.catalog.meta} title={product ? t.catalog.product.edit : t.catalog.product.new} />
      <div className="flex flex-col gap-4">
        <TextField
          label={t.catalog.product.name}
          required
          maxLength={300}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label={t.catalog.product.baseUnit}
            value={form.base_unit}
            options={BASE_UNITS.map((unit) => ({ value: unit, label: t.units[unit] }))}
            onChange={(e) => setForm({ ...form, base_unit: e.target.value as UnitCode })}
          />
          <TextField
            label={t.catalog.product.article}
            maxLength={100}
            value={form.article ?? ''}
            onChange={(e) => setForm({ ...form, article: e.target.value })}
          />
        </div>
        <p className="-mt-2 px-2 text-[12px] text-text-3">{t.catalog.product.baseUnitHint}</p>
        <SelectField
          label={t.catalog.product.category}
          value={form.category_id ?? ''}
          options={[
            { value: '', label: t.catalog.product.noCategory },
            ...categories.map((c) => ({ value: c.id, label: c.name })),
          ]}
          onChange={(e) => setForm({ ...form, category_id: e.target.value || null })}
        />
        {isAdmin && (
          <div className="flex items-end gap-2">
            <TextField
              className="flex-1"
              label={t.catalog.product.newCategory}
              maxLength={200}
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
            />
            <LaserButton
              type="button"
              variant="ghost"
              className="h-12"
              aria-label={t.catalog.add}
              icon={<Plus size={16} />}
              disabled={!newCategory.trim()}
              loading={addCategory.isPending}
              onClick={() => addCategory.mutate()}
            >
              {''}
            </LaserButton>
          </div>
        )}

        <FormError>{failure && describeError(failure, t)}</FormError>
        <LaserButton type="submit" size="lg" block icon={<Save size={16} />} loading={save.isPending} disabled={!form.name.trim()}>
          {t.catalog.save}
        </LaserButton>
        {product && !product.archived && (
          <LaserButton type="button" variant="danger" block icon={<Archive size={14} />} loading={archive.isPending} onClick={() => archive.mutate()}>
            {t.catalog.archive}
          </LaserButton>
        )}
      </div>
    </form>
  )
}
