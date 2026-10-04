import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { AlertTriangle, Camera, Check } from 'lucide-react'
import { useEffect, useState } from 'react'
import { expectedOrderQuery, type ExpectedLine, type PaymentMethod } from '@/entities/receipt'
import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import { cn } from '@/shared/lib/cn'
import { compressImage } from '@/shared/lib/image'
import { telegram } from '@/shared/lib/telegram'
import { uuid7 } from '@/shared/lib/uuid7'
import { enqueueReceipt } from '@/shared/offline/outbox'
import {
  Card,
  DiffIndicator,
  EmptyState,
  LaserButton,
  MoneyText,
  MonoLabel,
  PageHeader,
  QtyStepper,
  SegmentedControl,
  Skeleton,
  TextField,
} from '@/shared/ui'

// Ekrandagi ogohlantirish uchun; haqiqiy qaror — backend dopusklari (ZAKUP_RECEIVING_*)
const WEIGHT_TOLERANCE_PCT = 3
const DIVISIBLE_UNITS: ReadonlySet<UnitCode> = new Set(['kg', 'g', 'l', 'ml'])

interface LineFact {
  qty: number
  price: number
  defect: number
  defectReason: string
  open: boolean
}

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

export default function ReceiveOrderPage() {
  const { orderId } = useParams({ from: '/shell/receiving/$orderId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: order, isPending, isError } = useQuery(expectedOrderQuery(orderId))

  useEffect(() => telegram.backButton(() => navigate({ to: '/receiving' })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-96" />
  if (isError || !order) return <EmptyState code="404" title={t.receiving.orderNotFound} />
  return <ReceiveForm orderId={order.order_id} number={order.number} lines={order.lines} />
}

function ReceiveForm({ orderId, number, lines }: { orderId: string; number: string; lines: ExpectedLine[] }) {
  const { t, fmt } = useI18n()
  const navigate = useNavigate()
  // ID bir marta yaratiladi: qayta yuborish (oflayn navbat) shu ID bilan — dublikat bo'lmaydi
  const [receiptId] = useState(uuid7)
  const [facts, setFacts] = useState<Record<string, LineFact>>({})
  const [photo, setPhoto] = useState<Blob | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [invoiceNo, setInvoiceNo] = useState('')
  const [method, setMethod] = useState<PaymentMethod>('transfer')
  const [saving, setSaving] = useState(false)

  const factOf = (line: ExpectedLine): LineFact =>
    facts[line.order_line_id] ?? { qty: Number(line.qty), price: Number(line.price), defect: 0, defectReason: '', open: false }
  const update = (line: ExpectedLine, patch: Partial<LineFact>) =>
    setFacts((prev) => ({ ...prev, [line.order_line_id]: { ...factOf(line), ...patch } }))

  const total = lines.reduce((sum, line) => {
    const fact = factOf(line)
    return sum + Math.max(fact.qty - fact.defect, 0) * fact.price
  }, 0)
  const defectWithoutReason = lines.some((line) => factOf(line).defect > 0 && !factOf(line).defectReason.trim())

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  const takePhoto = async (file: File | undefined) => {
    if (!file) return
    const compressed = await compressImage(file)
    setPhoto(compressed)
    setPreview(URL.createObjectURL(compressed))
  }

  const complete = async () => {
    if (!photo) return
    setSaving(true)
    await enqueueReceipt({
      id: receiptId,
      orderId,
      orderNumber: number,
      photo,
      photoType: photo.type || 'image/jpeg',
      payload: {
        id: receiptId,
        order_id: orderId,
        supplier_invoice_no: invoiceNo.trim() || null,
        payment_method: method,
        lines: lines.map((line) => {
          const fact = factOf(line)
          return {
            order_line_id: line.order_line_id,
            qty: String(fact.qty),
            price: String(fact.price),
            qty_defect: String(fact.defect),
            defect_reason: fact.defectReason.trim() || null,
          }
        }),
      },
    })
    telegram.haptic.notify('success')
    void navigate({ to: '/receiving', replace: true })
  }

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={number} title={t.receiving.title} />

      <div className="flex flex-col gap-2">
        {lines.map((line, i) => {
          const fact = factOf(line)
          const unit = t.units[line.base_unit]
          const priceUp = fact.price > Number(line.price)
          return (
            <Card key={line.order_line_id} padded={false} className="p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <MonoLabel className="mb-1.5">{`${String(i + 1).padStart(2, '0')}/${t.receiving.position}`}</MonoLabel>
                  <div className="text-[15px] font-semibold">{line.product_name}</div>
                </div>
                <DiffIndicator
                  expected={Number(line.qty)}
                  actual={fact.qty}
                  unit={unit}
                  tolerancePct={DIVISIBLE_UNITS.has(line.base_unit) ? WEIGHT_TOLERANCE_PCT : 0}
                />
              </div>
              <QtyStepper
                label={`${line.product_name} — ${t.receiving.fact}`}
                value={fact.qty}
                step={DIVISIBLE_UNITS.has(line.base_unit) ? 0.5 : 1}
                unit={unit}
                onChange={(qty) => update(line, { qty, defect: Math.min(fact.defect, qty) })}
              />
              <button
                type="button"
                className="mt-3 flex w-full items-center justify-between text-[12px] text-text-2"
                onClick={() => update(line, { open: !fact.open })}
              >
                <span>{`${t.receiving.price}: ${fmt.money(fact.price)} / ${unit}`}</span>
                <span className={cn('flex items-center gap-1', (fact.defect > 0 || priceUp) && 'text-warning')}>
                  {(fact.defect > 0 || priceUp) && <AlertTriangle size={12} />}
                  {fact.defect > 0 ? `${t.receiving.defect}: ${fmt.qty(fact.defect)} ${unit}` : t.receiving.defect}
                </span>
              </button>
              {fact.open && (
                <div className="mt-3 flex flex-col gap-3 border-t border-border-soft pt-3">
                  <TextField
                    label={t.receiving.price}
                    inputMode="decimal"
                    suffix={`${t.common.currency}/${unit}`}
                    defaultValue={String(fact.price)}
                    onChange={(e) => update(line, { price: Number(decimal(e.target.value)) || 0 })}
                  />
                  <TextField
                    label={t.receiving.defectQty}
                    inputMode="decimal"
                    suffix={unit}
                    defaultValue={fact.defect ? String(fact.defect) : ''}
                    onChange={(e) => update(line, { defect: Math.min(Number(decimal(e.target.value)) || 0, fact.qty) })}
                  />
                  {fact.defect > 0 && (
                    <TextField
                      label={t.receiving.defectReason}
                      maxLength={500}
                      value={fact.defectReason}
                      onChange={(e) => update(line, { defectReason: e.target.value })}
                    />
                  )}
                </div>
              )}
            </Card>
          )
        })}
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <TextField label={t.receiving.invoiceNo} maxLength={100} value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
        <MonoLabel>{t.receiving.paymentMethod}</MonoLabel>
        <SegmentedControl
          segments={(['transfer', 'cash'] as const).map((value) => ({ value, label: t.paymentMethod[value] }))}
          value={method}
          onChange={setMethod}
        />
      </div>

      {/* Nakladnoy fotosi majburiy (WORKFLOW B8) */}
      <label
        className={cn(
          'mt-4 flex min-h-16 cursor-pointer items-center gap-3 rounded-row border border-dashed px-4 py-3 transition-colors',
          photo ? 'border-[var(--accent-border)] bg-accent-wash' : 'border-border',
        )}
      >
        {preview ? (
          <img src={preview} alt="" className="size-12 shrink-0 rounded-md object-cover" />
        ) : (
          <span className="grid size-10 place-items-center rounded-full bg-surface-2 text-text-2">
            <Camera size={18} />
          </span>
        )}
        <span className="min-w-0 flex-1">
          <MonoLabel className="mb-1">{t.receiving.invoicePhoto}</MonoLabel>
          <span className="block truncate text-sm text-text-2">{photo ? `${Math.round(photo.size / 1024)} KB` : t.receiving.takePhoto}</span>
        </span>
        {photo && <Check size={18} className="text-accent-text" />}
        <input type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => void takePhoto(e.target.files?.[0])} />
      </label>

      <div className="mt-6 flex items-center justify-between">
        <MonoLabel>{t.receiving.factTotal}</MonoLabel>
        <MoneyText value={total} className="text-lg" />
      </div>

      <LaserButton
        size="lg"
        block
        className="mt-4"
        disabled={!photo || defectWithoutReason}
        loading={saving}
        onClick={() => void complete()}
      >
        {t.receiving.complete}
      </LaserButton>
    </div>
  )
}
