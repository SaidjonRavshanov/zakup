import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Camera, ChevronDown, ChevronUp, Info, WifiOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { RECEIVABLE_STATUSES, purchaseOrdersQuery } from '@/entities/purchase-order'
import { expectedOrderQuery, type ExpectedLine, type PaymentMethod } from '@/entities/receipt'
import type { UnitCode } from '@/shared/i18n/keys'
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Blueprint, Btn, DropZone, Empty, Field, Input, Seg, Sheet, Skeleton, Stepper, Tag, toast, usePageActions } from '@/shared/kit'
import { parseDecimal } from '@/shared/lib/format'
import { compressImage } from '@/shared/lib/image'
import { uuid7 } from '@/shared/lib/uuid7'
import { enqueueReceipt } from '@/shared/offline/outbox'
import { L } from './i18n'
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

/** Manfiy bo'lmagan son yoki null (noto'g'ri kiritilgan). */
const parse = (raw: string): number | null => {
  const v = parseDecimal(raw)
  return v !== null && v >= 0 ? v : null
}
const raw = (value: number) => String(value).replace('.', ',')
/** Backend uchun: miqdor — 4, pul — 2 kasrgacha (float qoldiqlarisiz). */
const dec = (value: number, digits: 2 | 4) => String(Number(value.toFixed(digits)))

/** Kiritilgan ma'lumotlar qoralamasi (sessionStorage): sahifa yopilsa / qayta ochilsa yo'qolmasin. Foto saqlanmaydi. */
interface Draft {
  facts: Record<string, LineFact>
  invoiceNo: string
  method: PaymentMethod
  onSite?: boolean
}
const draftKey = (orderId: string) => `zakup.receive.${orderId}`

function readDraft(orderId: string): Draft | null {
  try {
    const text = sessionStorage.getItem(draftKey(orderId))
    return text ? (JSON.parse(text) as Draft) : null
  } catch {
    return null
  }
}

function writeDraft(orderId: string, draft: Draft | null): void {
  try {
    if (draft) sessionStorage.setItem(draftKey(orderId), JSON.stringify(draft))
    else sessionStorage.removeItem(draftKey(orderId))
  } catch {
    /* saqlab bo'lmasa — faqat xotirada */
  }
}

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
  const { z, f, locale } = useZk()
  const navigate = useNavigate()
  const online = useOnline()
  // Sarlavha uchun (oflayn bo'lsa keshdagi qabul ro'yxatidan)
  const { data: po } = useQuery({ ...purchaseOrdersQuery(RECEIVABLE_STATUSES), select: (list) => list.find((o) => o.id === orderId) })
  // ID bir marta yaratiladi: qayta yuborish (oflayn navbat) shu ID bilan — dublikat bo'lmaydi
  const [receiptId] = useState(uuid7)
  const [restored] = useState(() => readDraft(orderId))
  const [facts, setFacts] = useState<Record<string, LineFact>>(restored?.facts ?? {})
  const [photo, setPhoto] = useState<Blob | null>(null)
  const [photoName, setPhotoName] = useState('')
  const [preview, setPreview] = useState<string | null>(null)
  const [photoOpen, setPhotoOpen] = useState(false)
  const [invoiceNo, setInvoiceNo] = useState(restored?.invoiceNo ?? '')
  const [method, setMethod] = useState<PaymentMethod>(restored?.method ?? 'transfer')
  // Qarzga (default) yoki haydovchiga joyida to'langan — to'langan bo'lsa majburiyat darhol yopiladi
  const [onSite, setOnSite] = useState(restored?.onSite ?? false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const finished = useRef(false)

  // Har o'zgarishda qoralama saqlanadi (yakunlangandan keyin — yo'q)
  useEffect(() => {
    if (finished.current) return
    const empty = Object.keys(facts).length === 0 && !invoiceNo && method === 'transfer' && !onSite
    writeDraft(orderId, empty ? null : { facts, invoiceNo, method, onSite })
  }, [orderId, facts, invoiceNo, method, onSite])
  const fileRef = useRef<HTMLInputElement>(null)

  const factOf = (line: ExpectedLine): LineFact =>
    facts[line.order_line_id] ?? { qty: raw(Number(line.qty)), price: raw(Number(line.price)), defect: '0', reason: '', open: false }
  const update = (line: ExpectedLine, patch: Partial<LineFact>) =>
    setFacts((prev) => ({ ...prev, [line.order_line_id]: { ...factOf(line), ...patch } }))
  /** Raqamlar (noto'g'ri bo'lsa — null): brak — qabul qilingan miqdordan oshmaydi. */
  const parsed = (line: ExpectedLine) => {
    const fact = factOf(line)
    const qty = parse(fact.qty)
    const defect = parse(fact.defect)
    return { qty, price: parse(fact.price), defect: defect === null || qty === null ? defect : Math.min(defect, qty) }
  }
  const isBad = (line: ExpectedLine) => Object.values(parsed(line)).some((v) => v === null)
  /** Ekrandagi hisob uchun: noto'g'ri qiymat — 0. */
  const numbers = (line: ExpectedLine) => {
    const p = parsed(line)
    return { qty: p.qty ?? 0, price: p.price ?? 0, defect: p.defect ?? 0 }
  }

  const total = lines.reduce((sum, line) => {
    const n = numbers(line)
    return sum + Math.max(n.qty - n.defect, 0) * n.price
  }, 0)
  const badNumbers = lines.some(isBad)
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
    if (!photo || badNumbers || defectWithoutReason) return
    setSaving(true)
    setSaveError(null)
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
          paid_on_delivery: onSite,
          lines: lines.map((line) => {
            const n = numbers(line)
            return {
              order_line_id: line.order_line_id,
              qty: dec(n.qty, 4),
              price: dec(n.price, 2),
              qty_defect: dec(n.defect, 4),
              defect_reason: factOf(line).reason.trim() || null,
            }
          }),
        },
      })
    } catch (error) {
      // IndexedDB yo'q / joy tugagan — ma'lumot qoralamada qoladi, foydalanuvchi ko'radi
      setSaveError(`${L[locale].save_failed}: ${error instanceof Error ? error.message : String(error)}`)
      return
    } finally {
      setSaving(false)
    }
    finished.current = true
    writeDraft(orderId, null)
    toast(z.toast_recv_saved)
    void navigate({ to: '/receiving', replace: true })
  }

  usePageActions({
    primary: {
      label: z.a_finish,
      onClick: () => void complete(),
      disabled: !photo || defectWithoutReason || badNumbers,
      loading: saving,
    },
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
      {restored && !photo && <Banner tone="info">{L[locale].draft_restored}</Banner>}

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
          const p = parsed(line)
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
              {p.qty === null && <div className="mt-1 text-[13px] text-danger">{L[locale].bad_number_short}</div>}
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
                      <Input inputMode="decimal" value={fact.price} invalid={p.price === null} onChange={(e) => update(line, { price: e.target.value })} />
                    </Field>
                    <Field label={`${z.defect}, ${unit}`}>
                      <Input inputMode="decimal" value={fact.defect} invalid={p.defect === null} onChange={(e) => update(line, { defect: e.target.value })} />
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
        <Field label={z.pay_when}>
          <Seg
            options={[
              { value: 'debt', label: z.pay_debt },
              { value: 'site', label: z.pay_on_site },
            ]}
            value={onSite ? 'site' : 'debt'}
            onChange={(v) => setOnSite(v === 'site')}
          />
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

      <div className="mt-2 text-[13px] text-n7">{onSite ? z.pay_site_hint : z.pay_debt_hint}</div>

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
      {(!photo || defectWithoutReason || badNumbers) && (
        <div className="mt-2.5 flex items-center gap-2 text-[14px] text-warn">
          <Info size={20} className="shrink-0" />
          {badNumbers ? L[locale].bad_number : !photo ? z.need_photo : z.need_reason}
        </div>
      )}
      {saveError && <Banner tone="danger">{saveError}</Banner>}

      <Sheet open={photoOpen} title={invoiceNo.trim() ? `${z.invoice} ${invoiceNo.trim()}` : z.invoice_photo} onClose={() => setPhotoOpen(false)}>
        {preview && <img src={preview} alt={z.invoice_photo} className="w-full border border-line" />}
      </Sheet>
    </div>
  )
}
