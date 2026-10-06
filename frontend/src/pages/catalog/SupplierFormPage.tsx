/** /catalog/suppliers/new va /catalog/suppliers/$supplierId/edit — prototipda ekran yo'q, kit Field/Input/Seg/Chips bilan. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
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
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Chips, Empty, Field, Input, PageHead, RowsSkeleton, Seg, confirmAction, toast, usePageActions } from '@/shared/kit'
import { FormSection, SuffixInput } from './form-ui'
import { weekdayNames } from './format'

export default function SupplierFormPage() {
  const { supplierId } = useParams({ strict: false })
  const { z } = useZk()
  const { data: supplier, isPending } = useQuery({ ...supplierQuery(supplierId ?? ''), enabled: Boolean(supplierId) })

  if (supplierId && isPending) return <RowsSkeleton n={4} />
  if (supplierId && !supplier) return <Empty title={z.not_found} hint={z.not_found_hint} />
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
const toggleDay = (list: number[], day: number) => (list.includes(day) ? list.filter((d) => d !== day) : [...list, day]).sort((a, b) => a - b)

function SupplierForm({ supplier }: { supplier?: SupplierDetail }) {
  const { t } = useI18n()
  const { z } = useZk()
  const s = t.catalog.supplier
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<SupplierInput>(() => toInput(supplier))
  const set = <K extends keyof SupplierInput>(key: K, value: SupplierInput[K]) => setForm((prev) => ({ ...prev, [key]: value }))
  const setContact = (key: keyof SupplierInput['contacts'], value: string) =>
    setForm((prev) => ({ ...prev, contacts: { ...prev.contacts, [key]: value } }))

  const done = async (id: string) => {
    toast(z.toast_saved)
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

  const deferralInvalid = form.payment_terms === 'deferred' && !(form.deferral_days >= 1 && form.deferral_days <= 120)
  const valid = Boolean(form.name.trim()) && !deferralInvalid
  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    if (valid && !save.isPending) save.mutate()
  }
  const askArchive = async () => {
    if (await confirmAction({ title: `${t.catalog.archive}?`, body: supplier?.name, label: t.catalog.archive, cancel: z.cancel, danger: true }))
      archive.mutate()
  }
  const names = weekdayNames(z)
  const weekdayOptions = WEEKDAYS.map((d) => ({ value: String(d), label: names[d - 1] ?? String(d) }))
  const failure = save.error ?? archive.error

  usePageActions({
    primary: { label: z.a_save, onClick: () => submit(), disabled: !valid, loading: save.isPending },
    secondary:
      supplier && !supplier.archived ? { label: t.catalog.archive, danger: true, onClick: () => void askArchive() } : null,
  })

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-[720px]">
      <PageHead kicker={z.catalog} title={supplier ? s.edit : s.new} />
      <div className="mt-4 flex flex-col gap-4">
        <Field label={s.name}>
          <Input required maxLength={200} value={form.name} onChange={(e) => set('name', e.target.value)} />
        </Field>
        <Field label={s.inn}>
          <Input inputMode="numeric" maxLength={14} value={form.inn ?? ''} onChange={(e) => set('inn', e.target.value.replace(/\D/g, ''))} />
        </Field>

        <FormSection>{s.terms}</FormSection>
        <Field label={s.paymentTerms}>
          <Seg
            options={PAYMENT_TERMS.map((value) => ({ value, label: t.paymentTerms[value] }))}
            value={form.payment_terms}
            onChange={(value: PaymentTerms) => set('payment_terms', value)}
          />
        </Field>
        {form.payment_terms === 'deferred' && (
          <Field label={s.deferralDays}>
            <SuffixInput
              type="number"
              min={1}
              max={120}
              required
              invalid={deferralInvalid}
              suffix={z.days_s}
              value={form.deferral_days || ''}
              onChange={(e) => set('deferral_days', Number(e.target.value))}
            />
          </Field>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Field label={s.minOrder}>
            <SuffixInput
              inputMode="decimal"
              suffix={z.sum}
              value={form.min_order_amount}
              onChange={(e) => set('min_order_amount', e.target.value.replace(',', '.'))}
            />
          </Field>
          <Field label={s.creditLimit}>
            <SuffixInput
              inputMode="decimal"
              suffix={z.sum}
              value={form.credit_limit}
              onChange={(e) => set('credit_limit', e.target.value.replace(',', '.'))}
            />
          </Field>
        </div>

        <FormSection>{s.schedule}</FormSection>
        <div className="grid grid-cols-2 gap-3">
          <Field label={s.leadTime}>
            <SuffixInput
              type="number"
              min={0}
              max={60}
              suffix={z.days_s}
              value={form.lead_time_days}
              onChange={(e) => set('lead_time_days', Number(e.target.value))}
            />
          </Field>
          <Field label={s.cutoff}>
            <Input type="time" value={form.order_cutoff ?? ''} onChange={(e) => set('order_cutoff', e.target.value)} />
          </Field>
        </div>
        <Field label={s.orderDays}>
          <Chips
            options={weekdayOptions}
            value={form.order_weekdays.map(String)}
            onChange={(d) => set('order_weekdays', toggleDay(form.order_weekdays, Number(d)))}
          />
        </Field>
        <Field label={s.deliveryDays}>
          <Chips
            options={weekdayOptions}
            value={form.delivery_weekdays.map(String)}
            onChange={(d) => set('delivery_weekdays', toggleDay(form.delivery_weekdays, Number(d)))}
          />
        </Field>

        <FormSection>{s.contacts}</FormSection>
        <Field label={s.person}>
          <Input maxLength={200} value={form.contacts.person ?? ''} onChange={(e) => setContact('person', e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={s.phone}>
            <Input
              type="tel"
              placeholder="+998"
              maxLength={20}
              value={form.contacts.phone ?? ''}
              onChange={(e) => setContact('phone', e.target.value.replace(/[^\d+]/g, ''))}
            />
          </Field>
          <Field label={s.telegram}>
            <Input placeholder="@" maxLength={64} value={form.contacts.telegram ?? ''} onChange={(e) => setContact('telegram', e.target.value)} />
          </Field>
        </div>
        <Field label={s.email}>
          <Input type="email" maxLength={254} value={form.contacts.email ?? ''} onChange={(e) => setContact('email', e.target.value)} />
        </Field>

        {failure && <Banner tone="danger">{describeError(failure, t)}</Banner>}
      </div>
    </form>
  )
}
