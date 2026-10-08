/**
 * Yetkazuvchi uchun ro'yxatsiz sahifa: /s/{token} (WORKFLOW B7). Kirish talab qilinmaydi — imzolangan token yetarli,
 * shuning uchun AuthGate va ilova qobig'idan tashqarida chiziladi (app/main.tsx) — pastki panel shu yerda.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { toOrderLine, type LineResponseInput, type PurchaseOrderStatus } from '@/entities/purchase-order'
import { LanguageSwitch } from '@/features/language-switch'
import { ResponseLines, useResponseDrafts } from '@/features/order-response'
import { ApiError, apiRequest } from '@/shared/api/client'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import {
  ActionBar,
  Banner,
  Blueprint,
  ConfirmHost,
  Empty,
  RowsSkeleton,
  ToastHost,
  TotalLine,
  usePageActions,
} from '@/shared/kit'

interface PublicOrder {
  number: string
  supplier_name: string | null
  store_name: string | null
  delivery_date: string
  status: PurchaseOrderStatus
  total: string
  lines: Array<Parameters<typeof toOrderLine>[0]>
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-ground text-ink">
      <div className="mx-auto w-full max-w-[720px] flex-1 px-4 pb-8 pt-2">
        {children}
        <LanguageSwitch className="mt-8" />
      </div>
      <div className="sticky bottom-0 mx-auto w-full max-w-[720px]" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        <ActionBar wide={false} />
      </div>
      <ConfirmHost />
      <ToastHost />
    </div>
  )
}

export default function SupplierLinkPage({ token }: { token: string }) {
  const { z } = useZk()
  const { t } = useI18n()
  const order = useQuery({
    queryKey: ['public-order', token],
    queryFn: ({ signal }) => apiRequest<PublicOrder>(`/public/orders/${token}`, { signal, auth: false }),
    retry: false,
  })

  if (order.isPending)
    return (
      <Shell>
        <RowsSkeleton n={4} />
      </Shell>
    )
  if (order.error || !order.data) {
    const invalid = order.error instanceof ApiError && order.error.status === 401
    return (
      <Shell>
        <Empty title={invalid ? t.supplierLink.invalid : describeError(order.error, t)} hint={z.public_note} />
      </Shell>
    )
  }
  return <PublicOrderView token={token} data={order.data} onAnswered={() => order.refetch()} />
}

function PublicOrderView({ token, data, onAnswered }: { token: string; data: PublicOrder; onAnswered: () => unknown }) {
  const { z, f } = useZk()
  const { t } = useI18n()
  const lines = data.lines.map((line) => toOrderLine({ ...line, needs_reapproval: false }))
  const drafts = useResponseDrafts(lines)
  const respond = useMutation({
    mutationFn: (payload: LineResponseInput[]) =>
      apiRequest<{ status: PurchaseOrderStatus }>(`/public/orders/${token}/response`, {
        method: 'POST',
        body: { lines: payload },
        auth: false,
      }),
    onSuccess: () => onAnswered(),
  })
  const answered = data.status !== 'SENT'
  const form = !answered && !respond.isSuccess

  usePageActions(
    form
      ? {
          primary: {
            label: z.a_send_resp,
            onClick: () => respond.mutate(drafts.payload),
            disabled: !drafts.valid,
            loading: respond.isPending,
          },
          secondary: {
            label: z.a_confirm_all,
            onClick: () => respond.mutate(lines.map((l) => ({ line_id: l.id, kind: 'confirmed' as const }))),
            disabled: respond.isPending,
          },
        }
      : {},
  )

  return (
    <Shell>
      <div className="pt-2 text-[13px] text-n7">{z.public_note}</div>
      <h1 className="m-0 mt-1" style={{ fontSize: 34 }}>
        {z.order_from}
      </h1>
      <div className="text-[15px] text-n7">
        {`${data.number} · ${data.store_name ?? '—'} · ${z.delivery} ${f.dt(data.delivery_date)}`}
      </div>

      {form ? (
        <>
          <ResponseLines lines={lines} drafts={drafts} />
          <TotalLine label={z.total} value={f.money(drafts.total ?? data.total)} />
          {respond.error && <Banner tone="danger">{describeError(respond.error, t)}</Banner>}
        </>
      ) : (
        <Blueprint className="mt-6 px-4 py-8 text-center">
          <div className="font-head text-[26px]" style={{ fontWeight: 600 }}>
            {respond.isSuccess ? z.pub_thanks : z.pub_already}
          </div>
          {respond.isSuccess && <div className="text-[15px] text-n7">{z.pub_thanks_sub}</div>}
        </Blueprint>
      )}
    </Shell>
  )
}
