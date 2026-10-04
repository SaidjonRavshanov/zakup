import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Check, FileText, ImageIcon, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { FINANCE_KEY, PAYMENT_TONE, paymentQuery, paymentsApi, type PaymentDetail } from '@/entities/payment'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { loadFile, uploadFile, type LoadedFile } from '@/shared/api/files'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { compressImage } from '@/shared/lib/image'
import { telegram } from '@/shared/lib/telegram'
import { Card, EmptyState, FormError, LaserButton, MoneyText, MonoLabel, PageHeader, Skeleton, StatusBadge, TextField } from '@/shared/ui'

export default function PaymentPage() {
  const { paymentId } = useParams({ from: '/shell/finance/payments/$paymentId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: payment, isPending, error } = useQuery(paymentQuery(paymentId))

  useEffect(() => telegram.backButton(() => navigate({ to: '/finance' })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (error || !payment) return <EmptyState code="404" title={t.common.notFound} />
  return <PaymentView payment={payment} />
}

function PaymentView({ payment }: { payment: PaymentDetail }) {
  const { t, fmt } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const canApprove = useHasRole('approver', 'admin')
  const canPay = useHasRole('accountant', 'admin')
  const [reason, setReason] = useState('')
  const [rejecting, setRejecting] = useState(false)
  const [proof, setProof] = useState<File | Blob | null>(null)
  const [proofFile, setProofFile] = useState<LoadedFile | null>(null)

  const act = useMutation({
    mutationFn: async (action: 'approve' | 'reject' | 'cancel' | 'pay') => {
      if (action === 'approve') return paymentsApi.approve(payment.id)
      if (action === 'reject') return paymentsApi.reject(payment.id, reason.trim())
      if (action === 'cancel') return paymentsApi.cancel(payment.id)
      const proofId = proof ? await uploadFile('/finance/attachments', proof) : null
      return paymentsApi.pay(payment.id, proofId)
    },
    onSuccess: async () => {
      telegram.haptic.notify('success')
      setRejecting(false)
      await queryClient.invalidateQueries({ queryKey: FINANCE_KEY })
    },
  })

  useEffect(() => () => {
    if (proofFile) URL.revokeObjectURL(proofFile.url)
  }, [proofFile])

  const attach = async (file: File | undefined) => {
    if (file) setProof(file.type === 'application/pdf' ? file : await compressImage(file))
  }
  const showProof = async () => setProofFile(await loadFile(`/finance/attachments/${payment.proof_id}`))

  const active = payment.status === 'SUBMITTED' || payment.status === 'APPROVED'
  const timeline = [
    [t.finance.requested, payment.requested_at],
    [t.finance.approvedAt, payment.status !== 'REJECTED' ? payment.approved_at : null],
    [t.finance.paidAt, payment.paid_at],
  ] as const

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={`${payment.number} · ${t.paymentMethod[payment.method]}`}
        title={t.finance.title}
        action={<StatusBadge tone={PAYMENT_TONE[payment.status]}>{t.finance.paymentStatus[payment.status]}</StatusBadge>}
      />

      <Card index={`01/${t.finance.toPay}`} title={payment.supplier_name ?? '—'}>
        <MoneyText value={Number(payment.total)} className="mt-2 block text-2xl" />
        {payment.comment && <p className="mt-2 text-[13px] text-text-2">{payment.comment}</p>}
        <dl className="mt-3 flex flex-col gap-1 text-[12px]">
          {timeline
            .filter(([, at]) => at)
            .map(([label, at]) => (
              <div key={label} className="flex justify-between text-text-2">
                <dt>{label}</dt>
                <dd className="tnum">{`${fmt.date(at!)} ${fmt.time(at!)}`}</dd>
              </div>
            ))}
        </dl>
        {payment.decision_comment && (
          <p className={cn('mt-3 text-[13px]', payment.status === 'REJECTED' && 'text-danger')}>{payment.decision_comment}</p>
        )}
      </Card>

      <section className="mt-6 flex flex-col gap-2">
        <MonoLabel className="mb-1">{`02/${t.finance.invoices}`}</MonoLabel>
        {payment.lines.map((line) => (
          <button
            key={line.obligation_id}
            type="button"
            className="flex items-center justify-between rounded-row border border-border-soft bg-surface px-4 py-3 text-left shadow-[var(--shadow-card)]"
            onClick={() => navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: line.receipt_id } })}
          >
            <span>
              <span className="block text-[15px] font-semibold">{line.receipt_number}</span>
              <span className="text-[12px] text-text-2">{`${t.finance.outstanding}: ${fmt.money(Number(line.outstanding))}`}</span>
            </span>
            <MoneyText value={Number(line.amount)} className="text-[14px]" />
          </button>
        ))}
      </section>

      <section className="mt-6 flex flex-col gap-3">
        <FormError>{act.error && describeError(act.error, t)}</FormError>

        {payment.status === 'SUBMITTED' && canApprove && !rejecting && (
          <div className="grid grid-cols-2 gap-2">
            <LaserButton variant="ghost" icon={<X size={14} />} onClick={() => setRejecting(true)}>
              {t.finance.reject}
            </LaserButton>
            <LaserButton icon={<Check size={14} />} loading={act.isPending} onClick={() => act.mutate('approve')}>
              {t.finance.approve}
            </LaserButton>
          </div>
        )}
        {rejecting && (
          <>
            <TextField label={t.finance.rejectReason} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            <LaserButton block disabled={!reason.trim()} loading={act.isPending} onClick={() => act.mutate('reject')}>
              {t.finance.reject}
            </LaserButton>
          </>
        )}

        {payment.status === 'APPROVED' && canPay && (
          <>
            <label
              className={cn(
                'flex min-h-16 cursor-pointer items-center gap-3 rounded-row border border-dashed px-4 py-3',
                proof ? 'border-[var(--accent-border)] bg-accent-wash' : 'border-border',
              )}
            >
              <span className="grid size-10 place-items-center rounded-full bg-surface-2 text-text-2">
                <FileText size={18} />
              </span>
              <span className="min-w-0 flex-1">
                <MonoLabel className="mb-1">{t.finance.proof}</MonoLabel>
                <span className="block truncate text-sm text-text-2">
                  {proof ? `${Math.round(proof.size / 1024)} KB` : t.finance.attachProof}
                </span>
              </span>
              {proof && <Check size={18} className="text-accent-text" />}
              <input
                type="file"
                accept="image/*,application/pdf"
                className="sr-only"
                onChange={(e) => void attach(e.target.files?.[0])}
              />
            </label>
            <LaserButton size="lg" block loading={act.isPending} onClick={() => act.mutate('pay')}>
              {t.finance.pay}
            </LaserButton>
          </>
        )}

        {active && canPay && (
          <LaserButton variant="ghost" block loading={act.isPending} onClick={() => act.mutate('cancel')}>
            {t.finance.cancel}
          </LaserButton>
        )}

        {payment.proof_id &&
          (proofFile?.type.startsWith('image/') ? (
            <img src={proofFile.url} alt={t.finance.showProof} className="w-full rounded-card border border-border-soft" />
          ) : proofFile ? (
            <a href={proofFile.url} target="_blank" rel="noreferrer" className="text-center text-sm text-accent-text underline">
              {t.finance.showProof} (PDF)
            </a>
          ) : (
            <LaserButton variant="ghost" block icon={<ImageIcon size={14} />} onClick={() => void showProof()}>
              {t.finance.showProof}
            </LaserButton>
          ))}
      </section>
    </div>
  )
}
