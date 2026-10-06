import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Camera, FileText, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { FINANCE_KEY, paymentQuery, paymentsApi, type PaymentDetail } from '@/entities/payment'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { loadFile, uploadFile, type LoadedFile } from '@/shared/api/files'
import { useI18n } from '@/shared/i18n'
import { fill, useZk } from '@/shared/i18n/use-zk'
import {
  Banner,
  Blueprint,
  Btn,
  Empty,
  LinkRow,
  RowsSkeleton,
  Section,
  Sheet,
  Skeleton,
  Tag,
  Textarea,
  confirmAction,
  status,
  toast,
  usePageActions,
  type PageAction,
} from '@/shared/kit'
import { compressImage } from '@/shared/lib/image'

type Action = 'approve' | 'reject' | 'cancel' | 'pay'

export default function PaymentPage() {
  const { paymentId } = useParams({ from: '/shell/finance/payments/$paymentId' })
  const { z } = useZk()
  const { data: payment, isPending, error } = useQuery(paymentQuery(paymentId))

  if (isPending) return <RowsSkeleton n={5} />
  if (error || !payment) return <Empty title={z.not_found} />
  return <PaymentView payment={payment} />
}

function PaymentView({ payment }: { payment: PaymentDetail }) {
  const { t } = useI18n()
  const { z, f } = useZk()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const canApprove = useHasRole('approver', 'admin')
  const canPay = useHasRole('accountant', 'admin')
  const [reason, setReason] = useState('')
  const [rejecting, setRejecting] = useState(false)
  const [proof, setProof] = useState<File | Blob | null>(null)
  const [proofName, setProofName] = useState('')
  const [proofFile, setProofFile] = useState<LoadedFile | null>(null)
  const [proofOpen, setProofOpen] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const act = useMutation({
    mutationFn: async (action: Action) => {
      if (action === 'approve') return paymentsApi.approve(payment.id)
      if (action === 'reject') return paymentsApi.reject(payment.id, reason.trim())
      if (action === 'cancel') return paymentsApi.cancel(payment.id)
      const proofId = proof ? await uploadFile('/finance/attachments', proof) : null
      return paymentsApi.pay(payment.id, proofId)
    },
    onSuccess: async (_, action) => {
      const msg = { approve: z.toast_pay_approved, reject: z.toast_rejected, cancel: z.toast_cancelled, pay: z.toast_paid }
      toast(msg[action])
      setRejecting(false)
      setReason('')
      await queryClient.invalidateQueries({ queryKey: FINANCE_KEY })
    },
  })

  useEffect(() => () => {
    if (proofFile) URL.revokeObjectURL(proofFile.url)
  }, [proofFile])

  const attach = async (file: File | undefined) => {
    if (!file) return
    setProof(file.type === 'application/pdf' ? file : await compressImage(file))
    setProofName(file.name)
  }
  const showProof = async () => {
    const file = proofFile ?? (await loadFile(`/finance/attachments/${payment.proof_id}`).catch(() => null))
    if (!file) return toast(z.not_found)
    setProofFile(file)
    if (file.type.startsWith('image/')) setProofOpen(true)
    else window.open(file.url, '_blank', 'noopener')
  }

  const supplier = payment.supplier_name ?? '—'
  const active = payment.status === 'SUBMITTED' || payment.status === 'APPROVED'
  const canUpload = payment.status === 'APPROVED' && canPay

  let primary: PageAction | null = null
  let secondary: PageAction | null = null
  if (payment.status === 'SUBMITTED' && canApprove) {
    primary = { label: z.a_approve, onClick: () => act.mutate('approve'), loading: act.isPending && act.variables === 'approve' }
    secondary = { label: z.a_reject, onClick: () => setRejecting(true), danger: true }
  }
  if (payment.status === 'APPROVED' && canPay)
    primary = {
      label: z.a_paid,
      loading: act.isPending && act.variables === 'pay',
      onClick: async () => {
        const body = fill(z.cf_paid_body, { s: f.money(payment.total), n: supplier })
        if (await confirmAction({ title: z.cf_paid, body, label: z.a_paid, cancel: z.cancel })) act.mutate('pay')
      },
    }
  if (!secondary && active && canPay)
    secondary = {
      label: z.a_cancel_pay,
      danger: true,
      onClick: async () => {
        const ok = await confirmAction({
          title: fill(z.cf_cancel_pay, { id: payment.number }),
          body: z.cf_irrev,
          label: z.a_cancel_pay,
          cancel: z.cancel,
          danger: true,
        })
        if (ok) act.mutate('cancel')
      },
    }
  usePageActions({ primary, secondary })

  const s = status(z, 'payment', payment.status)
  const steps = [
    [z.tl_created, payment.requested_at],
    [z.tl_approved, payment.status !== 'REJECTED' ? payment.approved_at : null],
    [z.tl_paid, payment.paid_at],
  ] as const

  return (
    <div>
      <div className="flex items-start justify-between gap-3 pt-2">
        <div className="min-w-0">
          <div className="text-[14px] text-n7">{`${z.pay_req} · ${payment.method === 'cash' ? z.pay_cash : z.pay_bank}`}</div>
          <h1 className="m-0 text-[34px]">{payment.number}</h1>
        </div>
        <Tag tone={s.tone} className="mt-1.5 text-[13px]">
          {s.label}
        </Tag>
      </div>

      <Blueprint className="mt-4 p-4">
        <div className="text-[15px] font-medium">{supplier}</div>
        <div className="font-head text-[40px] leading-[1.1]" style={{ fontWeight: 600 }}>
          {f.money(payment.total)}
        </div>
        {payment.comment && <div className="text-[14px] text-n7">{payment.comment}</div>}
      </Blueprint>

      {payment.decision_comment &&
        (payment.status === 'REJECTED' ? (
          <Banner tone="danger" icon={<X size={20} />}>{`${z.reject_reason}: ${payment.decision_comment}`}</Banner>
        ) : (
          <div className="mt-3 text-[14px] text-n7">{payment.decision_comment}</div>
        ))}

      {act.error && <Banner tone="danger">{describeError(act.error, t)}</Banner>}

      <Section className="mb-2">{z.timeline}</Section>
      <div className="flex flex-col">
        {steps.map(([label, at]) => (
          <div
            key={label}
            className="grid min-h-11 items-center gap-2.5 border-b border-dashed border-line"
            style={{ gridTemplateColumns: '24px minmax(0,1fr) auto' }}
          >
            <span
              className="block size-3 justify-self-center"
              style={{ border: '1.5px solid var(--color-accent)', background: at ? 'var(--color-accent)' : 'transparent' }}
            />
            <span className="text-[15px]" style={{ color: at ? 'var(--color-text)' : 'var(--color-neutral-600)' }}>
              {label}
            </span>
            <span className="text-[13px] text-n7">{at ? f.dtTime(at) : '—'}</span>
          </div>
        ))}
      </div>

      <Section>{z.invoices}</Section>
      {payment.lines.map((line) => (
        <LinkRow
          key={line.obligation_id}
          aside={<span className="whitespace-nowrap text-[15px]">{f.money(line.amount)}</span>}
          onClick={() => navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: line.receipt_id } })}
        >
          <span className="font-medium">{line.receipt_number}</span>
          <span className="block text-[13px] text-n7">{`${z.debt}: ${f.money(line.outstanding)}`}</span>
        </LinkRow>
      ))}

      <Section className="mb-2">{z.pay_proof}</Section>
      {payment.proof_id && (
        <div className="flex items-center gap-3 border border-line p-2.5">
          <FileText size={20} />
          <span className="flex-1 text-[15px]">{z.pay_proof}</span>
          <Btn variant="ghost" size="sm" onClick={() => void showProof()}>
            {z.a_view}
          </Btn>
        </div>
      )}
      {canUpload && (
        <>
          <input
            ref={fileRef}
            type="file"
            accept="image/*,application/pdf"
            className="sr-only"
            onChange={(e) => {
              void attach(e.target.files?.[0])
              e.target.value = ''
            }}
          />
          {proof ? (
            <div className="mt-2 flex items-center gap-3 border border-line p-2.5">
              <FileText size={20} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[15px]">{proofName}</div>
                <div className="text-[13px] text-n7">{`${Math.round(proof.size / 1024)} ${z.kb}`}</div>
              </div>
              <Btn variant="ghost" size="sm" onClick={() => fileRef.current?.click()}>
                {z.a_change}
              </Btn>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="mt-2 flex min-h-[72px] w-full items-center justify-center gap-2 bg-transparent text-[16px] font-medium text-a7 hover:bg-a1"
              style={{ border: '1.5px dashed var(--color-accent)' }}
            >
              <Camera size={20} />
              {z.a_upload}
            </button>
          )}
        </>
      )}
      {!payment.proof_id && !canUpload && <div className="text-[14px] text-n7">{z.no_proof}</div>}

      <Sheet open={rejecting} title={z.reject_pay_title} onClose={() => setRejecting(false)}>
        <Textarea
          className="min-h-24"
          maxLength={500}
          value={reason}
          placeholder={z.reason_ph}
          autoFocus
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="mt-1.5 text-[13px] text-n7">{z.reason_req}</div>
        <div className="mt-4 flex gap-2.5">
          <Btn size="lg" className="flex-1" onClick={() => setRejecting(false)}>
            {z.cancel}
          </Btn>
          <Btn
            size="lg"
            className="flex-1"
            danger
            disabled={!reason.trim()}
            loading={act.isPending && act.variables === 'reject'}
            onClick={() => act.mutate('reject')}
          >
            {z.a_reject}
          </Btn>
        </div>
        {act.error && <Banner tone="danger">{describeError(act.error, t)}</Banner>}
      </Sheet>

      <Sheet open={proofOpen} title={z.pay_proof} onClose={() => setProofOpen(false)}>
        {proofFile ? <img src={proofFile.url} alt={z.pay_proof} className="w-full border border-line" /> : <Skeleton className="aspect-[3/4] w-full" />}
      </Sheet>
    </div>
  )
}
