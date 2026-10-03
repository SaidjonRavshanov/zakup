import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Archive, Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import {
  CATALOG_KEY,
  PAYMENT_TERMS,
  WEEKDAYS,
  catalogApi,
  supplierQuery,
  type PaymentTerms,
  type SupplierDetail,
  type SupplierInput,
} from '@/entities/catalog'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { ChipsField, EmptyState, FormError, LaserButton, MonoLabel, PageHeader, SelectField, Skeleton, TextField } from '@/shared/ui'

/** /catalog/suppliers/new va /catalog/suppliers/$supplierId/edit */
export default function SupplierFormPage() {
  const { supplierId } = useParams({ strict: false })
  const { data: supplier, isPending } = useQuery({ ...supplierQuery(supplierId ?? ''), enabled: Boolean(supplierId) })

  if (supplierId && isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (supplierId && !supplier) return <EmptyState code="404" title="404" />
  return <SupplierForm supplier={supplier} />
}

const toInput = (s?: SupplierDetail): SupplierInput => ({
  name: s?.name ?? '',
  inn: s?.inn ?? '',
  payment_terms: s?.payment_terms ?? 'on_delivery',
  deferral_days: s?.deferral_days ?? 0,
  credit_limit: s?.credit_limit ?? '0',
  min_order_amount: s?.min_order_amount ?? '0',
  lead_time_days: s?.lead_time_days ?? 1,
  order_weekdays: s?.order_weekdays ?? [...WEEKDAYS],
  delivery_weekdays: s?.delivery_weekdays ?? [...WEEKDAYS],
  order_cutoff: s?.order_cutoff?.slice(0, 5) ?? '',
  contacts: { phone: '', telegram: '', email: '', person: '', ...s?.contacts },
})

const blankToNull = (value: string | null | undefined) => value?.trim() || null

function SupplierForm({ supplier }: { supplier?: SupplierDetail }) {
  const { t } = useI18n()
  const s = t.catalog.supplier
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<SupplierInput>(() => toInput(supplier))
  const set = <K extends keyof SupplierInput>(key: K, value: SupplierInput[K]) => setForm((f) => ({ ...f, [key]: value }))
  const setContact = (key: keyof SupplierInput['contacts'], value: string) =>
    setForm((f) => ({ ...f, contacts: { ...f.contacts, [key]: value } }))

  const back = () =>
    supplier
      ? navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId: supplier.id } })
      : navigate({ to: '/catalog', search: { tab: 'suppliers' } })
  useEffect(() => telegram.backButton(back))

  const done = async (id: string) => {
    telegram.haptic.notify('success')
    await queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
    void navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId: id }, replace: true })
  }
  const save = useMutation({
    mutationFn: async () => {
      const body: SupplierInput = {
        ...form,
        name: form.name.trim(),
        inn: blankToNull(form.inn),
        deferral_days: form.payment_terms === 'deferred' ? form.deferral_days : 0,
        credit_limit: form.credit_limit || '0',
        min_order_amount: form.min_order_amount || '0',
        order_cutoff: blankToNull(form.order_cutoff),
        contacts: Object.fromEntries(Object.entries(form.contacts).map(([k, v]) => [k, blankToNull(v)])),
      }
      if (!supplier) return (await catalogApi.createSupplier(body)).id
      await catalogApi.updateSupplier(supplier.id, body)
      return supplier.id
    },
    onSuccess: done,
  })
  const archive = useMutation({ mutationFn: () => catalogApi.archiveSupplier(supplier!.id), onSuccess: () => done(supplier!.id) })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }
  const weekdayOptions = WEEKDAYS.map((d) => ({ value: d, label: t.weekdays[d - 1] ?? String(d) }))
  const failure = save.error ?? archive.error

  return (
    <form onSubmit={submit} className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.catalog.meta} title={supplier ? s.edit : s.new} />
      <div className="flex flex-col gap-4">
        <TextField label={s.name} required maxLength={200} value={form.name} onChange={(e) => set('name', e.target.value)} />
        <TextField
          label={s.inn}
          inputMode="numeric"
          maxLength={14}
          value={form.inn ?? ''}
          onChange={(e) => set('inn', e.target.value.replace(/\D/g, ''))}
        />

        <MonoLabel className="mt-2">{s.terms}</MonoLabel>
        <SelectField
          label={s.paymentTerms}
          value={form.payment_terms}
          options={PAYMENT_TERMS.map((value) => ({ value, label: t.paymentTerms[value] }))}
          onChange={(e) => set('payment_terms', e.target.value as PaymentTerms)}
        />
        {form.payment_terms === 'deferred' && (
          <TextField
            label={s.deferralDays}
            type="number"
            min={1}
            max={120}
            required
            value={form.deferral_days || ''}
            onChange={(e) => set('deferral_days', Number(e.target.value))}
          />
        )}
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label={s.minOrder}
            inputMode="decimal"
            suffix={t.common.currency}
            value={form.min_order_amount}
            onChange={(e) => set('min_order_amount', e.target.value.replace(',', '.'))}
          />
          <TextField
            label={s.creditLimit}
            inputMode="decimal"
            suffix={t.common.currency}
            value={form.credit_limit}
            onChange={(e) => set('credit_limit', e.target.value.replace(',', '.'))}
          />
        </div>

        <MonoLabel className="mt-2">{s.schedule}</MonoLabel>
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label={s.leadTime}
            type="number"
            min={0}
            max={60}
            value={form.lead_time_days}
            onChange={(e) => set('lead_time_days', Number(e.target.value))}
          />
          <TextField label={s.cutoff} type="time" value={form.order_cutoff ?? ''} onChange={(e) => set('order_cutoff', e.target.value)} />
        </div>
        <ChipsField label={s.orderDays} options={weekdayOptions} value={form.order_weekdays} onChange={(v) => set('order_weekdays', v.sort())} />
        <ChipsField
          label={s.deliveryDays}
          options={weekdayOptions}
          value={form.delivery_weekdays}
          onChange={(v) => set('delivery_weekdays', v.sort())}
        />

        <MonoLabel className="mt-2">{s.contacts}</MonoLabel>
        <TextField label={s.person} maxLength={200} value={form.contacts.person ?? ''} onChange={(e) => setContact('person', e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label={s.phone}
            type="tel"
            placeholder="+998"
            maxLength={20}
            value={form.contacts.phone ?? ''}
            onChange={(e) => setContact('phone', e.target.value.replace(/[^\d+]/g, ''))}
          />
          <TextField
            label={s.telegram}
            placeholder="@"
            maxLength={64}
            value={form.contacts.telegram ?? ''}
            onChange={(e) => setContact('telegram', e.target.value)}
          />
        </div>
        <TextField label={s.email} type="email" maxLength={254} value={form.contacts.email ?? ''} onChange={(e) => setContact('email', e.target.value)} />

        <FormError>{failure && describeError(failure, t)}</FormError>
        <LaserButton type="submit" size="lg" block icon={<Save size={16} />} loading={save.isPending} disabled={!form.name.trim()}>
          {t.catalog.save}
        </LaserButton>
        {supplier && !supplier.archived && (
          <LaserButton type="button" variant="danger" block icon={<Archive size={14} />} loading={archive.isPending} onClick={() => archive.mutate()}>
            {t.catalog.archive}
          </LaserButton>
        )}
      </div>
    </form>
  )
}
