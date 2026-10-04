/**
 * Yetkazuvchi uchun ro'yxatsiz sahifa: /s/{token} (WORKFLOW B7). Kirish talab qilinmaydi — imzolangan token yetarli,
 * shuning uchun AuthGate va ilova qobig'idan tashqarida chiziladi (app/main.tsx).
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { toOrderLine, type LineResponseInput, type PurchaseOrderStatus } from '@/entities/purchase-order'
import { ResponseForm } from '@/features/order-response'
import { LanguageSwitch } from '@/features/language-switch'
import { ApiError, apiRequest } from '@/shared/api/client'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { EmptyState, FormError, MoneyText, MonoLabel, Skeleton, StatusBadge } from '@/shared/ui'

interface PublicOrder {
  number: string
  supplier_name: string | null
  store_name: string | null
  delivery_date: string
  status: PurchaseOrderStatus
  total: string
  lines: Array<Parameters<typeof toOrderLine>[0]>
}

const COMPANY = 'Tarnov'

export default function SupplierLinkPage({ token }: { token: string }) {
  const { t, fmt } = useI18n()
  const order = useQuery({
    queryKey: ['public-order', token],
    queryFn: ({ signal }) => apiRequest<PublicOrder>(`/public/orders/${token}`, { signal, auth: false }),
    retry: false,
  })
  const respond = useMutation({
    mutationFn: (lines: LineResponseInput[]) =>
      apiRequest<{ status: PurchaseOrderStatus }>(`/public/orders/${token}/response`, {
        method: 'POST',
        body: { lines },
        auth: false,
      }),
    onSuccess: () => order.refetch(),
  })

  const shell = (children: React.ReactNode) => (
    <div className="mx-auto min-h-dvh max-w-xl px-4 py-8 animate-[enter_0.5s_var(--ease-expo)_both]">
      {children}
      <LanguageSwitch className="mt-8" />
    </div>
  )

  if (order.isPending) return shell(<Skeleton className="h-[300px]" />)
  if (order.error || !order.data) {
    const invalid = order.error instanceof ApiError && order.error.status === 401
    return shell(<EmptyState code="401" title={invalid ? t.supplierLink.invalid : describeError(order.error, t)} />)
  }

  const data = order.data
  const lines = data.lines.map((line) => toOrderLine({ ...line, needs_reapproval: false }))
  const answered = data.status !== 'SENT'

  return shell(
    <>
      <MonoLabel className="mb-3">{`${data.number} · ${data.store_name ?? ''}`}</MonoLabel>
      <h1 className="font-display text-[30px] font-extrabold uppercase leading-[0.95] tracking-[-0.05em]">
        {t.supplierLink.from(COMPANY)}
      </h1>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <StatusBadge tone={answered ? 'accent' : 'info'}>{t.poStatus[data.status]}</StatusBadge>
        <span className="text-[13px] text-text-2">{`${t.orderPage.delivery}: ${fmt.date(data.delivery_date)}`}</span>
      </div>

      <div className="mt-5 flex flex-col gap-2">
        {lines.map((line) => (
          <div key={line.id} className="flex items-start justify-between gap-3 rounded-row border border-border-soft bg-surface px-4 py-3">
            <div className="min-w-0">
              <div className="text-[15px] font-semibold">{line.productName}</div>
              <div className="mt-0.5 text-[12px] text-text-2">
                {`${fmt.qty(line.qtyOrdered)} ${t.units[line.unit]} × ${fmt.money(line.priceOrdered)}`}
              </div>
              {line.response && (
                <div className="mt-1 text-[12px] text-accent-text">
                  {t.orderPage.responseKinds[line.response]}
                  {line.response === 'price_changed' && line.priceConfirmed !== null && `: ${fmt.money(line.priceConfirmed)}`}
                  {line.response === 'qty_changed' && line.qtyConfirmed !== null && `: ${fmt.qty(line.qtyConfirmed)} ${t.units[line.unit]}`}
                </div>
              )}
            </div>
            <MoneyText value={line.amount} className="shrink-0 text-[13px]" />
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-baseline justify-between px-1">
        <MonoLabel>{t.requests.total}</MonoLabel>
        <MoneyText value={Number(data.total)} className="text-lg" />
      </div>

      {answered ? (
        <p className="mt-6 rounded-row border border-[var(--accent-border)] bg-accent-wash px-4 py-3 text-[14px]">
          {respond.isSuccess ? t.supplierLink.thanks : t.supplierLink.alreadyAnswered}
        </p>
      ) : (
        <>
          <p className="mt-6 text-[13px] text-text-2">{t.supplierLink.hint}</p>
          <ResponseForm lines={lines} busy={respond.isPending} submitLabel={t.supplierLink.send} onSubmit={(payload) => respond.mutate(payload)} />
          <FormError>{respond.error && describeError(respond.error, t)}</FormError>
        </>
      )}
    </>,
  )
}
