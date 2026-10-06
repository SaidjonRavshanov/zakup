import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Camera, ChevronDown, ChevronUp, Info, WifiOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { purchaseOrdersQuery } from '@/entities/purchase-order'
import { expectedOrderQuery, type ExpectedLine, type PaymentMethod } from '@/entities/receipt'
import type { UnitCode } from '@/shared/i18n/keys'
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Blueprint, Btn, DropZone, Empty, Field, Input, Seg, Sheet, Skeleton, Stepper, Tag, toast, usePageActions } from '@/shared/kit'
import { compressImage } from '@/shared/lib/image'
import { uuid7 } from '@/shared/lib/uuid7'
import { enqueueReceipt } from '@/shared/offline/outbox'
import { useOnline } from './use-online'

// Ekrandagi ogohlantirish uchun; haqiqiy qaror — backend dopusklari (ZAKUP_RECEIVING_*)
const WEIGHT_TOLERANCE_PCT = 3
const DIVISIBLE_UNITS: ReadonlySet<UnitCode> = new Set(['kg', 'g', 'l', 'ml'])

/** Foydalanuvchi kiritayotgan matnlar (vergul ham, nuqta ham). */
interface LineFact {
  qty: string
  price: string
  defect: string
  reason: string
  open: boolean
}

const parse = (raw: string) => {
  const v = Number(raw.replace(/\s/g, '').replace(',', '.').replace(/[^\d.]/g, ''))
  return Number.isFinite(v) ? v : 0
}
const raw = (value: number) => String(value).replace('.', ',')

export default function ReceiveOrderPage() {
  const { orderId } = useParams({ from: '/shell/receiving/$orderId' })
  const { z } = useZk()
  const { data: order, isPending, isError } = useQuery(expectedOrderQuery(orderId))

  if (isPending)
    return (
      <div className="flex flex-col gap-4 pt-2">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    )
  if (isError || !order) return <Empty title={z.not_found} />
  return <ReceiveForm orderId={order.order_id} number={order.number} lines={order.lines} />
}

function ReceiveForm({ orderId, number, lines }: { orderId: string; number: string; lines: ExpectedLine[] }) {
  const { z, f } = useZk()
  const navigate = useNavigate()
  const online = useOnline()
  // Sarlavha uchun (oflayn bo'lsa keshdagi ro'yxatdan)
  const { data: po } = useQuery({ ...purchaseOrdersQuery(), select: (list) => list.find((o) => o.id === orderId) })
  // ID bir marta yaratiladi: qayta yuborish (oflayn navbat) shu ID bilan — dublikat bo'lmaydi
  const [receiptId] = useState(uuid7)
  const [facts, setFacts] = useState<Record<string, LineFact>>({})
  const [photo, setPhoto] = useState<Blob | null>(null)
  const [photoName, setPhotoName] = useState('')
  const [preview, setPreview] = useState<string | null>(null)
  const [photoOpen, setPhotoOpen] = useState(false)
  const [invoiceNo, setInvoiceNo] = useState('')
  const [method, setMethod] = useState<PaymentMethod>('transfer')
  const [saving, setSaving] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const factOf = (line: ExpectedLine): LineFact =>
    facts[line.order_line_id] ?? { qty: raw(Number(line.qty)), price: raw(Number(line.price)), defect: '0', reason: '', open: false }
  const update = (line: ExpectedLine, patch: Partial<LineFact>) =>
    setFacts((prev) => ({ ...prev, [line.order_line_id]: { ...factOf(line), ...patch } }))
  /** Raqamlar: brak — qabul qilingan miqdordan oshmaydi. */
  const numbers = (line: ExpectedLine) => {
    const fact = factOf(line)
    const qty = parse(fact.qty)
    return { qty, price: parse(fact.price), defect: Math.min(parse(fact.defect), qty) }
  }

  const total = lines.reduce((sum, line) => {
    const n = numbers(line)
    return sum + Math.max(n.qty - n.defect, 0) * n.price
  }, 0)
  const ordered = lines.reduce((sum, line) => sum + Number(line.qty) * Number(line.price), 0)
  const needsReason = (line: ExpectedLine) => numbers(line).defect > 0 && !factOf(line).reason.trim()
  const defectWithoutReason = lines.some(needsReason)

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  const takePhoto = async (file: File | undefined) => {
    if (!file) return
    const compressed = await compressImage(file)
    setPhoto(compressed)
    setPhotoName(file.name)
    setPreview(URL.createObjectURL(compressed))
  }

  const complete = async () => {
    if (!photo) return
    setSaving(true)
    try {
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
            const n = numbers(line)
            return {
              order_line_id: line.order_line_id,
              qty: String(n.qty),
              price: String(n.price),
              qty_defect: String(n.defect),
              defect_reason: factOf(line).reason.trim() || null,
            }
          }),
        },
      })
    } finally {
      setSaving(false)
    }
    toast(z.toast_recv_saved)
    void navigate({ to: '/receiving', replace: true })
  }

  usePageActions({
    primary: { label: z.a_finish, onClick: () => void complete(), disabled: !photo || defectWithoutReason, loading: saving },
  })

  return (
    <div>
      <div className="pt-2">
        <div className="text-[14px] text-n7">{po ? `${number} · ${po.storeName} · ${f.dt(po.deliveryDate)}` : number}</div>
        <h1 className="m-0 text-[32px]">{po?.supplierName ?? z.receiving}</h1>
      </div>

      {!online && (
        <Banner tone="warn" icon={<WifiOff size={20} />}>
          {z.offline_recv}
        </Banner>
      )}

      <div className="mt-5 flex flex-col gap-5">
        {lines.map((line) => {
          const fact = factOf(line)
          const n = numbers(line)
          const unit = f.unit(line.base_unit)
          const divisible = DIVISIBLE_UNITS.has(line.base_unit)
          const tol = divisible ? WEIGHT_TOLERANCE_PCT : 0
          const expected = Number(line.qty)
          const dev = expected ? ((n.qty - expected) / expected) * 100 : 0
          const out = Math.abs(dev) > tol + 1e-9
          const needR = needsReason(line)
          const priceUp = n.price > Number(line.price)
          const extra =
            (n.defect > 0 ? `${needR ? z.need_reason_short : `${z.defect} ${f.qty(n.defect, line.base_unit)}`} · ` : '') +
            `${f.money(n.price)} / ${unit}`
          return (
            <Blueprint key={line.order_line_id} className="p-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="text-[18px] font-medium leading-tight">{line.product_name}</div>
                <Tag tone={out ? 'warn' : 'ok'} className="text-[13px]">
                  {Math.abs(dev) < 1e-9 ? `= ${z.as_ordered}` : `${dev > 0 ? '▲' : '▼'} ${f.n(Math.abs(dev), 1)}%`}
                </Tag>
              </div>
              <div className="mb-2.5 mt-0.5 text-[14px] text-n7">
                {`${z.ordered}: ${f.qty(expected, line.base_unit)} · ${z.tol} ${tol ? `±${tol}%` : '0%'}`}
              </div>
              <Stepper
                label={`${line.product_name} — ${z.receiving}`}
                value={fact.qty}
                step={divisible ? 0.5 : 1}
                unit={unit}
                onChange={(qty) => update(line, { qty })}
              />
              <button
                type="button"
                onClick={() => update(line, { open: !fact.open })}
                className="mt-1.5 flex min-h-11 w-full items-center gap-2 text-left text-[14px] text-ink"
              >
                <span className="font-medium">{z.price_defect}</span>
                <span className={needR ? 'flex-1 text-danger' : priceUp || n.defect > 0 ? 'flex-1 text-warn' : 'flex-1 text-n7'}>
                  {extra}
                </span>
                {fact.open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {fact.open && (
                <>
                  <div className="grid grid-cols-2 gap-2.5">
                    <Field label={`${z.price_per} ${unit}`}>
                      <Input inputMode="decimal" value={fact.price} onChange={(e) => update(line, { price: e.target.value })} />
                    </Field>
                    <Field label={`${z.defect}, ${unit}`}>
                      <Input inputMode="decimal" value={fact.defect} onChange={(e) => update(line, { defect: e.target.value })} />
                    </Field>
                  </div>
                  <Field label={z.defect_reason} className="mt-2.5">
                    <Input
                      maxLength={500}
                      value={fact.reason}
                      invalid={needR}
                      placeholder={z.defect_reason_ph}
                      onChange={(e) => update(line, { reason: e.target.value })}
                    />
                  </Field>
                </>
              )}
            </Blueprint>
          )
        })}
      </div>

      <div className="mt-6 grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
        <Field label={z.inv_no}>
          <Input maxLength={100} value={invoiceNo} placeholder="MB-2291" onChange={(e) => setInvoiceNo(e.target.value)} />
        </Field>
        <Field label={z.pay_method}>
          <Seg
            options={[
              { value: 'transfer', label: z.pay_bank },
              { value: 'cash', label: z.pay_cash },
            ]}
            value={method}
            onChange={setMethod}
          />
        </Field>
      </div>

      {/* Nakladnoy fotosi majburiy (WORKFLOW B8) */}
      <div className="mb-2 mt-5 text-[13px] font-medium text-n7">{z.invoice_photo}</div>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={(e) => {
          void takePhoto(e.target.files?.[0])
          e.target.value = ''
        }}
      />
      {photo && preview ? (
        <div className="flex items-center gap-3 border border-line p-2.5">
          <button type="button" onClick={() => setPhotoOpen(true)} className="h-[76px] w-[60px] shrink-0 border border-line" aria-label={z.invoice_photo}>
            <img src={preview} alt="" className="size-full object-cover" />
          </button>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[15px] font-medium">{photoName || z.invoice_photo}</div>
            <div className="text-[13px] text-n7">{`${Math.round(photo.size / 1024)} ${z.kb}`}</div>
          </div>
          <Btn variant="ghost" onClick={() => fileRef.current?.click()}>
            {z.a_reshoot}
          </Btn>
        </div>
      ) : (
        <DropZone icon={<Camera size={22} />} title={z.a_shoot} hint={z.photo_required} onClick={() => fileRef.current?.click()} />
      )}

      <div className="mt-3 flex items-baseline justify-between gap-3 border-t border-line pb-1 pt-4">
        <span className="text-[15px] text-n7">{z.sum_fact}</span>
        <span className="whitespace-nowrap font-head text-[28px]" style={{ fontWeight: 600 }}>
          {f.money(total)}
        </span>
      </div>
      <div className="text-right text-[13px] text-n7">{`${z.ordered}: ${f.money(ordered)}`}</div>
      {(!photo || defectWithoutReason) && (
        <div className="mt-2.5 flex items-center gap-2 text-[14px] text-warn">
          <Info size={20} />
          {!photo ? z.need_photo : z.need_reason}
        </div>
      )}

      <Sheet open={photoOpen} title={invoiceNo.trim() ? `${z.invoice} ${invoiceNo.trim()}` : z.invoice_photo} onClose={() => setPhotoOpen(false)}>
        {preview && <img src={preview} alt={z.invoice_photo} className="w-full border border-line" />}
      </Sheet>
    </div>
  )
}
