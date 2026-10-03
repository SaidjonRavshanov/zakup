import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { DatabaseZap, ReceiptText } from 'lucide-react'
import { useEffect } from 'react'
import { iikoSyncQuery, requestIikoSync, type SyncKind, type SyncRun, type SyncStatus } from '@/entities/iiko'
import { CATALOG_KEY } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { Card, EmptyState, FormError, LaserButton, MonoLabel, PageHeader, Skeleton, StatusBadge, type Tone } from '@/shared/ui'

const STATUS_TONE: Record<SyncStatus, Tone> = { queued: 'neutral', running: 'info', done: 'accent', failed: 'danger' }

/** Natija: eng muhim sonlar (to'liq ro'yxat — backend logida). */
const STAT_KEYS = ['products_new', 'products', 'suppliers_new', 'suppliers', 'stores', 'prices_recorded', 'invoices'] as const

export default function IikoSyncPage() {
  const { t, fmt } = useI18n()
  const queryClient = useQueryClient()
  const isAdmin = useHasRole('admin')
  const { data, isPending, error } = useQuery(iikoSyncQuery)

  const request = useMutation({
    mutationFn: requestIikoSync,
    onSuccess: () => {
      telegram.haptic.notify('success')
      return queryClient.invalidateQueries({ queryKey: iikoSyncQuery.queryKey })
    },
  })

  // Yangi sinxron tugagach katalog keshi eskiradi
  const lastDone = data?.runs.find((run) => run.status === 'done')?.id
  useEffect(() => {
    if (lastDone) void queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
  }, [lastDone, queryClient])

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (error || !data) return <EmptyState code="403" title={t.errors.permission_denied} />

  const latest = (server: string, kind: SyncKind) => data.runs.find((r) => r.server_code === server && r.kind === kind)
  const busy = (server: string, kind: SyncKind) => {
    const run = latest(server, kind)
    return run?.status === 'queued' || run?.status === 'running'
  }

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.iiko.meta} title={t.iiko.title} />
      <p className="-mt-2 mb-4 text-[13px] text-text-2">{t.iiko.hint}</p>

      {data.servers.length === 0 && <EmptyState code="0" title={t.iiko.noServers} description={t.iiko.noServersHint} />}

      <div className="flex flex-col gap-3">
        {data.servers.map((server, i) => {
          const refs = latest(server.code, 'references')
          const prices = latest(server.code, 'purchase_prices')
          return (
            <Card key={server.code} index={`0${i + 1}/${t.iiko.department} ${server.department_code ?? '—'}`} title={server.name}>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-text-2">
                <span>
                  {t.iiko.kind.references}: {refs?.finished_at ? fmt.date(refs.finished_at) + ' ' + fmt.time(refs.finished_at) : '—'}
                </span>
                <span>
                  {t.iiko.kind.purchase_prices}:{' '}
                  {prices?.finished_at ? fmt.date(prices.finished_at) + ' ' + fmt.time(prices.finished_at) : '—'}
                </span>
              </div>
              {isAdmin && (
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <LaserButton
                    variant="ghost"
                    icon={<DatabaseZap size={14} />}
                    loading={busy(server.code, 'references')}
                    onClick={() => request.mutate({ server_code: server.code, kind: 'references' })}
                  >
                    {t.iiko.kind.references}
                  </LaserButton>
                  <LaserButton
                    variant="ghost"
                    icon={<ReceiptText size={14} />}
                    loading={busy(server.code, 'purchase_prices')}
                    onClick={() => request.mutate({ server_code: server.code, kind: 'purchase_prices', days: 30 })}
                  >
                    {t.iiko.kind.purchase_prices}
                  </LaserButton>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      <FormError>{request.error && describeError(request.error, t)}</FormError>

      <section className="mt-6">
        <MonoLabel className="mb-3">{t.iiko.history}</MonoLabel>
        {data.runs.length === 0 ? (
          <p className="px-2 text-sm text-text-3">{t.iiko.noRuns}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {data.runs.map((run) => (
              <RunRow key={run.id} run={run} serverName={data.servers.find((s) => s.code === run.server_code)?.name} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function RunRow({ run, serverName }: { run: SyncRun; serverName?: string }) {
  const { t, fmt } = useI18n()
  const stats = STAT_KEYS.filter((key) => run.stats[key]).map((key) => `${t.iiko.stats[key]}: ${fmt.qty(run.stats[key] ?? 0)}`)
  return (
    <div className="rounded-row border border-border-soft bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <MonoLabel className="mb-1.5 truncate">{`${serverName ?? run.server_code} · ${fmt.date(run.created_at)} ${fmt.time(run.created_at)}`}</MonoLabel>
          <div className="text-[15px] font-semibold">{t.iiko.kind[run.kind]}</div>
        </div>
        <StatusBadge tone={STATUS_TONE[run.status]}>{t.iiko.status[run.status]}</StatusBadge>
      </div>
      {stats.length > 0 && <p className="mt-2 text-[12px] text-text-2">{stats.join(' · ')}</p>}
      {run.error && <p className="mt-2 break-words text-[12px] text-danger">{run.error}</p>}
    </div>
  )
}
