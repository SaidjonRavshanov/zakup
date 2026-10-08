import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { ChevronRight, FileText, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ORDERS_KEY } from '@/entities/purchase-order'
import {
  RECEIPTS_KEY,
  RESOLUTIONS,
  receiptQuery,
  resolveDispute,
  type Discrepancy,
  type ReceiptDetail,
  type ReceiptLine,
  type Resolution,
} from '@/entities/receipt'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { loadFile } from '@/shared/api/files'
import { useI18n } from '@/shared/i18n'
import { useZk, type ZkKey } from '@/shared/i18n/use-zk'
import { Banner, Blueprint, Btn, Cells, Empty, KV, RowsSkeleton, Section, Sheet, Skeleton, Tag, Textarea, status, toast, usePageActions } from '@/shared/kit'
import { cn } from '@/shared/lib/cn'

const RESOLUTION_KEY: Record<Resolution, ZkKey> = {
  accepted: 'res_fact',
  return: 'res_return',
  discount: 'res_discount',
  replacement: 'res_replace',
}

export default function ReceiptPage() {
  const { receiptId } = useParams({ from: '/shell/receiving/receipts/$receiptId' })
  const { z } = useZk()
  const { data: receipt, isPending, error } = useQuery(receiptQuery(receiptId))

  if (isPending) return <RowsSkeleton n={5} />
  if (error || !receipt) return <Empty title={z.not_found} />
  return <ReceiptView receipt={receipt} />
}

function ReceiptView({ receipt }: { receipt: ReceiptDetail }) {
  const { t } = useI18n()
  const { z, f } = useZk()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isDecider = useHasRole('approver', 'buyer', 'admin')
  const [resolution, setResolution] = useState<Resolution>('accepted')
  const [comment, setComment] = useState('')
  const [photoOpen, setPhotoOpen] = useState(false)
  const [photoUrl, setPhotoUrl] = useState<string | null>(null)
  const [photoFailed, setPhotoFailed] = useState(false)

  const disputeOpen = receipt.dispute !== null && receipt.dispute.resolution === null
  const canResolve = disputeOpen && isDecider

  const resolve = useMutation({
    mutationFn: () => resolveDispute(receipt.id, resolution, comment.trim()),
    onSuccess: async () => {
      toast(z.toast_resolved)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: RECEIPTS_KEY }),
        queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
      ])
    },
  })

  usePageActions({
    primary: canResolve
      ? { label: z.a_resolve, onClick: () => resolve.mutate(), disabled: !comment.trim(), loading: resolve.isPending }
      : null,
  })

  const showPhoto = async () => {
    setPhotoOpen(true)
    if (photoUrl) return
    setPhotoFailed(false)
    const file = await loadFile(`/receiving/attachments/${receipt.invoice_photo_id}`).catch(() => null)
    if (file) setPhotoUrl(file.url)
    else setPhotoFailed(true)
  }
  useEffect(() => () => {
    if (photoUrl) URL.revokeObjectURL(photoUrl)
  }, [photoUrl])

  const byLine = new Map<string, Discrepancy[]>()
  for (const d of receipt.discrepancies) byLine.set(d.line_id, [...(byLine.get(d.line_id) ?? []), d])

  const s = status(z, 'receipt', receipt.status)
  const ik = receipt.export_status ? status(z, 'iiko', receipt.export_status) : null
  const invoiceTitle = receipt.supplier_invoice_no ? `${z.invoice} ${receipt.supplier_invoice_no}` : z.invoice_photo

  /** Farq yorlig'i (prototip: dopusk ichida — kul rang, aks holda — ogohlantirish). */
  const discrepancyTag = (d: Discrepancy, line: ReceiptLine) => {
    const exp = Number(d.expected)
    const act = Number(d.actual)
    const pct = exp ? f.n((Math.abs(act - exp) / exp) * 100, 1) + '%' : ''
    const label: Record<Discrepancy['kind'], string> = {
      short: z.d_none,
      qty_under: `${z.d_short} ${pct}`,
      qty_over: `${z.d_over} ${pct}`,
      price_up: `${z.d_priceup} ${pct}`,
      price_down: `${z.d_pricedown} ${pct}`,
      defect: `${z.d_defect} ${f.qty(line.qty_defect, line.base_unit)}`,
    }
    const inTol = d.kind === 'price_down' || (d.within_tolerance && d.kind !== 'defect' && d.kind !== 'short')
    return (
      <Tag key={d.kind} tone={inTol ? 'neutral' : 'warn'}>
        {inTol ? `${label[d.kind]} · ${z.in_tol}` : label[d.kind]}
      </Tag>
    )
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-3 pt-2">
        <div className="min-w-0">
          <div className="text-[14px] text-n7">{`${z.receipt_act} · ${f.dtTime(receipt.received_at)}`}</div>
          <h1 className="m-0 text-[34px]">{receipt.number}</h1>
        </div>
        <Tag tone={s.tone} className="mt-1.5 text-[13px]">
          {s.label}
        </Tag>
      </div>

      <div className="mt-3">
        <KV
          rows={[
            [z.supplier, receipt.supplier_name ?? '—'],
            [z.store, receipt.store_name ?? '—'],
            [z.inv_no, receipt.supplier_invoice_no ?? '—'],
            [z.pay_when, receipt.paid_on_delivery ? z.pay_on_site : z.pay_debt],
            [z.pay_method, receipt.payment_method ? (receipt.payment_method === 'cash' ? z.pay_cash : z.pay_bank) : '—'],
            [
              'iiko',
              <span key="ik" className="inline-flex items-center gap-2">
                {receipt.iiko_document_number && <span>{receipt.iiko_document_number}</span>}
                {ik ? <Tag tone={ik.tone}>{ik.label}</Tag> : '—'}
              </span>,
            ],
          ]}
        />
        {receipt.export_error && <div className="break-words py-2 text-[14px] text-danger">{receipt.export_error}</div>}
      </div>

      <Cells
        className="mt-4"
        cols={2}
        size={21}
        items={[
          { label: z.sum_fact, value: f.money(receipt.total) },
          { label: z.ordered, value: f.money(receipt.expected_total) },
        ]}
      />

      <Section>{z.positions}</Section>
      {receipt.lines.map((line) => {
        const found = byLine.get(line.id) ?? []
        return (
          <div key={line.id} className="flex flex-col gap-1.5 border-b border-line py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="text-[16px] font-medium">{line.product_name}</div>
              <div className="whitespace-nowrap text-[15px]">{f.money(line.amount)}</div>
            </div>
            <div className="text-[14px] text-n7">
              {`${f.qty(line.qty_expected, line.base_unit)} → ${f.qty(line.qty_fact, line.base_unit)} · ${f.money(line.price_fact)} / ${f.unit(line.base_unit)}`}
            </div>
            {line.defect_reason && <div className="text-[14px]">{`${z.defect_reason}: ${line.defect_reason}`}</div>}
            {found.length > 0 && <div className="flex flex-wrap gap-1.5">{found.map((d) => discrepancyTag(d, line))}</div>}
          </div>
        )
      })}

      {receipt.dispute && (
        <Blueprint className="mt-6 px-4 py-3.5">
          <div className="flex items-center gap-2 font-head text-[20px]" style={{ fontWeight: 600 }}>
            <TriangleAlert size={20} />
            {z.dispute}
          </div>
          {disputeOpen && <div className="mt-1 text-[14px] text-warn">{z.dispute_open}</div>}
          {canResolve && (
            <>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {RESOLUTIONS.map((value) => {
                  const on = value === resolution
                  return (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setResolution(value)}
                      className={cn('min-h-11 border border-line px-2 text-[15px]', !on && 'zk-hover')}
                      style={on ? { background: 'var(--color-accent)', color: 'var(--color-bg)' } : { color: 'var(--color-text)' }}
                    >
                      {z[RESOLUTION_KEY[value]]}
                    </button>
                  )
                })}
              </div>
              <Textarea
                className="mt-2.5"
                maxLength={500}
                value={comment}
                placeholder={z.comment_req}
                onChange={(e) => setComment(e.target.value)}
              />
              {resolve.error && <Banner tone="danger">{describeError(resolve.error, t)}</Banner>}
            </>
          )}
          {receipt.dispute.resolution && (
            <div className="mt-1.5 text-[15px]">
              {`${z.decision}: ${z[RESOLUTION_KEY[receipt.dispute.resolution]]}`}
              {receipt.dispute.comment && ` — ${receipt.dispute.comment}`}
            </div>
          )}
        </Blueprint>
      )}

      <div className="mt-5 flex flex-wrap gap-2">
        <Btn icon={<FileText size={20} />} onClick={() => void showPhoto()}>
          {z.invoice}
        </Btn>
        <Btn variant="ghost" onClick={() => navigate({ to: '/orders/$orderId', params: { orderId: receipt.order_id } })}>
          {z.order}
          <ChevronRight size={20} />
        </Btn>
      </div>

      <Sheet open={photoOpen} title={invoiceTitle} onClose={() => setPhotoOpen(false)}>
        {photoUrl ? (
          <img src={photoUrl} alt={z.invoice_photo} className="w-full border border-line" />
        ) : photoFailed ? (
          <Empty title={z.not_found} />
        ) : (
          <Skeleton className="mx-auto aspect-[3/4] max-h-[420px] w-full" />
        )}
      </Sheet>
    </div>
  )
}
