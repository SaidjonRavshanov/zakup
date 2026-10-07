/** /catalog/products/new va /catalog/products/$productId/edit — prototipda ekran yo'q, kit Field/Input/Seg bilan. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { BASE_UNITS, CATALOG_KEY, catalogApi, categoriesQuery, productQuery, type ProductDetail, type ProductInput } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import type { UnitCode } from '@/shared/i18n/keys'
import { Banner, Btn, Empty, Field, Input, PageHead, RowsSkeleton, Seg, confirmAction, toast, usePageActions } from '@/shared/kit'
import { Select } from './form-ui'

export default function ProductFormPage() {
  const params = useParams({ strict: false })
  const productId = params.productId
  const { z } = useZk()
  const { data: product, isPending } = useQuery({ ...productQuery(productId ?? ''), enabled: Boolean(productId) })

  if (productId && isPending) return <RowsSkeleton n={4} />
  if (productId && !product) return <Empty title={z.not_found} hint={z.not_found_hint} />
  return <ProductForm product={product} />
}

function ProductForm({ product }: { product?: ProductDetail }) {
  const { t } = useI18n()
  const { z, f } = useZk()
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
  const newCategoryId = useId()

  const done = async (id: string) => {
    toast(z.toast_saved)
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
      setForm((prev) => ({ ...prev, category_id: id }))
      setNewCategory('')
    },
  })

  const valid = Boolean(form.name.trim())
  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    if (valid && !save.isPending) save.mutate()
  }
  const askArchive = async () => {
    if (await confirmAction({ title: `${t.catalog.archive}?`, body: product?.name, label: t.catalog.archive, cancel: z.cancel, danger: true }))
      archive.mutate()
  }
  const failure = save.error ?? archive.error ?? addCategory.error

  usePageActions({
    primary: { label: z.a_save, onClick: () => submit(), disabled: !valid, loading: save.isPending },
    secondary:
      product && !product.archived ? { label: t.catalog.archive, danger: true, onClick: () => void askArchive() } : null,
  })

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-[720px]">
      <PageHead kicker={z.catalog} title={product ? t.catalog.product.edit : t.catalog.product.new} />
      <div className="mt-4 flex flex-col gap-4">
        <Field label={t.catalog.product.name}>
          <Input required maxLength={300} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label={t.catalog.product.baseUnit} hint={t.catalog.product.baseUnitHint}>
          <Seg
            options={BASE_UNITS.map((unit) => ({ value: unit, label: f.unit(unit) }))}
            value={form.base_unit}
            onChange={(unit: UnitCode) => setForm({ ...form, base_unit: unit })}
          />
        </Field>
        <Field label={t.catalog.product.article}>
          <Input maxLength={100} value={form.article ?? ''} onChange={(e) => setForm({ ...form, article: e.target.value })} />
        </Field>
        <Field label={t.catalog.product.category}>
          <Select
            value={form.category_id ?? ''}
            options={[{ value: '', label: t.catalog.product.noCategory }, ...categories.map((c) => ({ value: c.id, label: c.name }))]}
            onChange={(e) => setForm({ ...form, category_id: e.target.value || null })}
          />
        </Field>
        {isAdmin && (
          <Field label={t.catalog.product.newCategory} id={newCategoryId}>
            <div className="flex gap-2">
              <Input
                id={newCategoryId}
                className="flex-1"
                maxLength={200}
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                onKeyDown={(e) => {
                  // Enter — butun formani emas, faqat kategoriyani qo'shadi
                  if (e.key !== 'Enter') return
                  e.preventDefault()
                  if (newCategory.trim() && !addCategory.isPending) addCategory.mutate()
                }}
              />
              <Btn
                icon={<Plus size={20} />}
                disabled={!newCategory.trim()}
                loading={addCategory.isPending}
                onClick={() => addCategory.mutate()}
              >
                {z.a_add}
              </Btn>
            </div>
          </Field>
        )}
        {failure && <Banner tone="danger">{describeError(failure, t)}</Banner>}
      </div>
    </form>
  )
}
