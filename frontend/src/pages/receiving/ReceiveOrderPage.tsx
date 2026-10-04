import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Camera, Check } from 'lucide-react'
import { useEffect, useState } from 'react'
import { PO_STATUS_TONE, purchaseOrderQuery, type PurchaseOrderLine } from '@/entities/purchase-order'
import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import { Card, DiffIndicator, EmptyState, LaserButton, MonoLabel, MoneyText, PageHeader, QtyStepper, Skeleton, StatusBadge } from '@/shared/ui'

// TODO(settings): dopusk backend sozlamalaridan keladi (platform.settings)
const QTY_TOLERANCE_PCT = 3
// Kasr miqdorli birliklar (vazn / hajm) — qolganlari butun son
const DIVISIBLE_UNITS: ReadonlySet<UnitCode> = new Set(['kg', 'g', 'l', 'ml'])

export default function ReceiveOrderPage() {
  const { orderId } = useParams({ from: '/shell/receiving/$orderId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: order, isPending, isError } = useQuery(purchaseOrderQuery(orderId))
  const [facts, setFacts] = useState<Record<string, number>>({})
  const [photo, setPhoto] = useState<File | null>(null)

  useEffect(() => telegram.backButton(() => navigate({ to: '/receiving' })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-96" />
  if (isError) return <EmptyState code="404" title={t.receiving.orderNotFound} />

  const factOf = (line: PurchaseOrderLine) => facts[line.id] ?? line.qtyOrdered
  const factTotal = order.lines.reduce((sum, line) => sum + factOf(line) * line.priceOrdered, 0)

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={`${order.number} · ${order.storeName}`}
        title={t.receiving.title}
        action={<StatusBadge tone={PO_STATUS_TONE[order.status]}>{t.poStatus[order.status]}</StatusBadge>}
      />
      <div className="mb-4 font-display text-lg font-extrabold uppercase tracking-[-0.03em]">{order.supplierName}</div>

      <div className="flex flex-col gap-2">
        {order.lines.map((line, i) => (
          <Card key={line.id} padded={false} className="p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <MonoLabel className="mb-1.5">{String(i + 1).padStart(2, '0')}/{t.receiving.position}</MonoLabel>
                <div className="truncate text-[15px] font-semibold">{line.productName}</div>
              </div>
              <DiffIndicator expected={line.qtyOrdered} actual={factOf(line)} unit={t.units[line.unit]} tolerancePct={QTY_TOLERANCE_PCT} />
            </div>
            <QtyStepper
              label={`${line.productName} — ${t.receiving.fact}`}
              value={factOf(line)}
              step={DIVISIBLE_UNITS.has(line.unit) ? 0.5 : 1}
              unit={t.units[line.unit]}
              onChange={(value) => setFacts((prev) => ({ ...prev, [line.id]: value }))}
            />
          </Card>
        ))}
      </div>

      {/* Nakladnoy fotosi majburiy (WORKFLOW B8) */}
      <label
        className={cn(
          'mt-4 flex h-16 cursor-pointer items-center gap-3 rounded-row border border-dashed px-4 transition-colors',
          photo ? 'border-[var(--accent-border)] bg-accent-wash' : 'border-border',
        )}
      >
        <span className={cn('grid size-10 place-items-center rounded-full', photo ? 'bg-accent text-accent-ink' : 'bg-surface-2 text-text-2')}>
          {photo ? <Check size={18} /> : <Camera size={18} />}
        </span>
        <span className="min-w-0 flex-1">
          <MonoLabel className="mb-1">{t.receiving.invoicePhoto}</MonoLabel>
          <span className="block truncate text-sm text-text-2">{photo ? photo.name : t.receiving.takePhoto}</span>
        </span>
        <input type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
      </label>

      <div className="mt-6 flex items-center justify-between">
        <MonoLabel>{t.receiving.factTotal}</MonoLabel>
        <MoneyText value={factTotal} className="text-lg" />
      </div>

      <LaserButton
        size="lg"
        block
        className="mt-4"
        disabled={!photo}
        onClick={() => {
          // TODO(receiving API): POST /receipts/{id}/submit (Idempotency-Key, oflayn outbox)
          telegram.haptic.notify('success')
          navigate({ to: '/receiving' })
        }}
      >
        {t.receiving.complete}
      </LaserButton>
    </div>
  )
}
