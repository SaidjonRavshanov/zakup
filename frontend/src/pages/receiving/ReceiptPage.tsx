import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Check, ImageIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ORDERS_KEY } from '@/entities/purchase-order'
import {
  EXPORT_STATUS_TONE,
  RECEIPTS_KEY,
  RECEIPT_STATUS_TONE,
  RESOLUTIONS,
  receiptQuery,
  resolveDispute,
  type ReceiptDetail,
  type Resolution,
} from '@/entities/receipt'
import { useHasRole } from '@/entities/user'
import { session } from '@/shared/api/session'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import { Card, EmptyState, FormError, LaserButton, MoneyText, MonoLabel, PageHeader, SelectField, Skeleton, StatusBadge, TextField } from '@/shared/ui'

export default function ReceiptPage() {
  const { receiptId } = useParams({ from: '/shell/receiving/receipts/$receiptId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: receipt, isPending, error } = useQuery(receiptQuery(receiptId))

  useEffect(() => telegram.backButton(() => navigate({ to: '/receiving' })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (error || !receipt) return <EmptyState code="404" title={t.common.notFound} />
  return <ReceiptView receipt={receipt} />
}

function ReceiptView({ receipt }: { receipt: ReceiptDetail }) {
  const { t, fmt } = useI18n()
  const queryClient = useQueryClient()
  const isDecider = useHasRole('approver', 'buyer', 'admin')
  const [resolution, setResolution] = useState<Resolution>('accepted')
  const [comment, setComment] = useState('')
  const [photoUrl, setPhotoUrl] = useState<string | null>(null)

  const resolve = useMutation({
    mutationFn: () => resolveDispute(receipt.id, resolution, comment.trim()),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: RECEIPTS_KEY }),
        queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
      ])
    },
  })

  // Foto — avtorizatsiya bilan (img src'ga token qo'yib bo'lmaydi) → blob URL
  const showPhoto = async () => {
    const response = await fetch(`/api/v1/receiving/attachments/${receipt.invoice_photo_id}`, {
      headers: { Authorization: `Bearer ${session.accessToken() ?? ''}` },
    })
    if (response.ok) setPhotoUrl(URL.createObjectURL(await response.blob()))
  }
  useEffect(() => () => {
    if (photoUrl) URL.revokeObjectURL(photoUrl)
  }, [photoUrl])

  const byLine = new Map<string, typeof receipt.discrepancies>()
  for (const d of receipt.discrepancies) byLine.set(d.line_id, [...(byLine.get(d.line_id) ?? []), d])
  const disputeOpen = receipt.dispute !== null && receipt.dispute.resolution === null

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={`${receipt.number} · ${receipt.store_name ?? '—'}`}
        title={t.receiving.title}
        action={<StatusBadge tone={RECEIPT_STATUS_TONE[receipt.status]}>{t.receiving.status[receipt.status]}</StatusBadge>}
      />

      <Card index={`01/${fmt.date(receipt.received_at)} ${fmt.time(receipt.received_at)}`} title={receipt.supplier_name ?? '—'}>
        <div className="mt-2 flex flex-wrap gap-2 text-[12px] text-text-2">
          {receipt.supplier_invoice_no && <span>{`№ ${receipt.supplier_invoice_no}`}</span>}
          {receipt.payment_method && <StatusBadge>{t.paymentMethod[receipt.payment_method]}</StatusBadge>}
          {receipt.export_status && (
            <StatusBadge tone={EXPORT_STATUS_TONE[receipt.export_status]}>{t.receiving.exportStatus[receipt.export_status]}</StatusBadge>
          )}
        </div>
        {receipt.iiko_document_number && (
          <p className="mt-2 text-[12px] text-text-3">{`${t.receiving.iikoDocument}: ${receipt.iiko_document_number}`}</p>
        )}
        {receipt.export_error && <p className="mt-2 break-words text-[12px] text-danger">{receipt.export_error}</p>}
        <div className="mt-3 flex items-baseline justify-between">
          <MonoLabel>{t.receiving.factTotal}</MonoLabel>
          <MoneyText value={Number(receipt.total)} className="text-lg" />
        </div>
        <div className="mt-1 flex items-baseline justify-between text-text-3">
          <MonoLabel>{t.receiving.expected}</MonoLabel>
          <MoneyText value={Number(receipt.expected_total)} className="text-[13px] font-normal" />
        </div>
      </Card>

      <section className="mt-6 flex flex-col gap-2">
        <MonoLabel className="mb-1">{`02/${t.requests.lines}`}</MonoLabel>
        {receipt.lines.map((line) => {
          const unit = t.units[line.base_unit]
          const found = byLine.get(line.id) ?? []
          return (
            <div key={line.id} className="rounded-row border border-border-soft bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 text-[15px] font-semibold">{line.product_name}</div>
                <MoneyText value={Number(line.amount)} className="shrink-0 text-[13px]" />
              </div>
              <div className="tnum mt-1 text-[12px] text-text-2">
                {`${fmt.qty(Number(line.qty_expected))} → ${fmt.qty(Number(line.qty_fact))} ${unit} · ${fmt.money(Number(line.price_fact))}`}
                {Number(line.qty_defect) > 0 && ` · ${t.receiving.defect} ${fmt.qty(Number(line.qty_defect))} ${unit}`}
              </div>
              {line.defect_reason && <p className="mt-1 text-[12px] text-text-3">{line.defect_reason}</p>}
              {found.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {found.map((d) => (
                    <StatusBadge key={d.kind} tone={d.kind === 'price_down' ? 'accent' : d.within_tolerance ? 'neutral' : 'warning'}>
                      {d.within_tolerance && d.kind !== 'price_down'
                        ? `${t.receiving.discrepancy[d.kind]} · ${t.receiving.withinTolerance}`
                        : t.receiving.discrepancy[d.kind]}
                    </StatusBadge>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </section>

      {receipt.dispute && (
        <section className={cn('mt-6 rounded-card border p-4', disputeOpen ? 'border-warning/40' : 'border-border-soft')}>
          <MonoLabel className="mb-2">{t.receiving.dispute}</MonoLabel>
          {disputeOpen ? (
            <>
              <p className="text-[13px] text-text-2">{t.receiving.disputeHint}</p>
              {isDecider && (
                <div className="mt-3 flex flex-col gap-3">
                  <SelectField
                    label={t.receiving.resolve}
                    value={resolution}
                    options={RESOLUTIONS.map((value) => ({ value, label: t.receiving.resolution[value] }))}
                    onChange={(e) => setResolution(e.target.value as Resolution)}
                  />
                  <TextField label={t.receiving.resolveComment} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
                  <FormError>{resolve.error && describeError(resolve.error, t)}</FormError>
                  <LaserButton block icon={<Check size={14} />} disabled={!comment.trim()} loading={resolve.isPending} onClick={() => resolve.mutate()}>
                    {t.receiving.resolve}
                  </LaserButton>
                </div>
              )}
            </>
          ) : (
            <p className="text-[13px]">
              <span className="font-semibold">{receipt.dispute.resolution && t.receiving.resolution[receipt.dispute.resolution]}</span>
              {receipt.dispute.comment && ` — ${receipt.dispute.comment}`}
            </p>
          )}
        </section>
      )}

      <section className="mt-6">
        {photoUrl ? (
          <img src={photoUrl} alt={t.receiving.photo} className="w-full rounded-card border border-border-soft" />
        ) : (
          <LaserButton variant="ghost" block icon={<ImageIcon size={14} />} onClick={() => void showPhoto()}>
            {t.receiving.photo}
          </LaserButton>
        )}
      </section>
    </div>
  )
}
