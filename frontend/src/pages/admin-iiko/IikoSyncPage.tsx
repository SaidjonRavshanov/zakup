/** iiko sinxroni (prototip "iiko", vmIiko): har server — blueprint karta, 4 tur + "Запустить"; pastda tarix. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { CATALOG_KEY } from '@/entities/catalog'
import { iikoSyncQuery, requestIikoSync, type SyncKind, type SyncRun } from '@/entities/iiko'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk, type ZkKey } from '@/shared/i18n/use-zk'
import { Banner, Btn, Corners, Empty, RowsSkeleton, Section, Tag, status, toast } from '@/shared/kit'

/** Natija: eng muhim sonlar (to'liq ro'yxat — backend logida). */
const STAT_KEYS = [
  'products_new',
  'products',
  'suppliers_new',
  'suppliers',
  'stores',
  'prices_recorded',
  'invoices',
  'balances',
  'days_products',
] as const

/** Har ertalab worker o'zi ham ishga tushiradi; tugmalar — qo'lda yangilash uchun. */
const KINDS: ReadonlyArray<{ kind: SyncKind; label: ZkKey; days?: number }> = [
  { kind: 'references', label: 'ik_ref' },
  { kind: 'purchase_prices', label: 'ik_prices', days: 30 },
  { kind: 'stock', label: 'ik_stock' },
  { kind: 'consumption', label: 'ik_usage', days: 28 },
]

const LABEL = Object.fromEntries(KINDS.map((k) => [k.kind, k.label])) as Record<SyncKind, ZkKey>
const active = (run?: SyncRun) => run?.status === 'queued' || run?.status === 'running'

export default function IikoSyncPage() {
  const { t } = useI18n()
  const { z, f } = useZk()
  const queryClient = useQueryClient()
  const isAdmin = useHasRole('admin')
  const { data, isPending, error } = useQuery(iikoSyncQuery)

  const request = useMutation({
    mutationFn: requestIikoSync,
    onSuccess: () => {
      toast(z.job_queued)
      return queryClient.invalidateQueries({ queryKey: iikoSyncQuery.queryKey })
    },
  })

  // Yangi sinxron tugagach katalog keshi eskiradi
  const lastDone = data?.runs.find((run) => run.status === 'done')?.id
  useEffect(() => {
    if (lastDone) void queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
  }, [lastDone, queryClient])

  if (isPending) return <RowsSkeleton n={5} />
  if (error || !data) return <Empty title={z.not_found} hint={z.not_found_hint} />

  const latest = (server: string, kind: SyncKind) => data.runs.find((r) => r.server_code === server && r.kind === kind)
  const serverName = (code: string) => data.servers.find((s) => s.code === code)?.name ?? code

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 pt-2">
        <h1 className="m-0 text-[34px]">{z.iiko_sync}</h1>
        {data.runs.some(active) && <span className="text-[13px] text-a7">{z.auto_refresh}</span>}
      </div>

      {data.servers.length === 0 && <Empty title={t.iiko.noServers} hint={t.iiko.noServersHint} />}
      {request.error && <Banner tone="danger">{describeError(request.error, t)}</Banner>}

      <div className="mt-4 grid gap-5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
        {data.servers.map((server) => (
          <div key={server.code} className="blueprint px-3.5 py-3">
            <Corners />
            <div className="font-head text-[22px]" style={{ fontWeight: 600 }}>
              {server.name}
            </div>
            {KINDS.map(({ kind, label, days }) => {
              const run = latest(server.code, kind)
              const busy = active(run)
              const failed = run?.status === 'failed'
              const at = run ? f.dtTime(run.finished_at ?? run.created_at) : '—'
              return (
                <div key={kind} className="flex min-h-12 items-center gap-3 border-t border-line">
                  <div className="min-w-0 flex-1">
                    <div className="text-[15px]">{z[label]}</div>
                    <div
                      className="text-[13px]"
                      style={{ color: busy ? 'var(--color-accent-700)' : failed ? 'var(--zk-danger)' : 'var(--color-neutral-700)' }}
                    >
                      {busy ? z.job_run : run ? `${failed ? z.err_last : z.last_ok} · ${at}` : '—'}
                    </div>
                  </div>
                  {isAdmin && (
                    <Btn
                      className="min-h-10 min-w-[84px]"
                      disabled={busy || request.isPending}
                      loading={request.isPending && request.variables?.server_code === server.code && request.variables.kind === kind}
                      style={{ opacity: busy ? 0.5 : 1 }}
                      onClick={() => request.mutate({ server_code: server.code, kind, days })}
                    >
                      {busy ? '…' : z.a_run}
                    </Btn>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>

      <Section>{z.history}</Section>
      {data.runs.length === 0 ? (
        <div className="py-4 text-[15px] text-n7">{t.iiko.noRuns}</div>
      ) : (
        data.runs.map((run) => {
          const s = status(z, 'job', run.status)
          const stats = STAT_KEYS.filter((key) => run.stats[key]).map((key) => `${t.iiko.stats[key]}: ${f.n(run.stats[key] ?? 0)}`)
          return (
            <div key={run.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 border-b border-line py-3">
              <div className="text-[15px] font-medium">
                {serverName(run.server_code)} · {z[LABEL[run.kind]]}
              </div>
              <Tag tone={s.tone} className="justify-self-end">
                {s.label}
              </Tag>
              <div className="col-span-2 text-[13px] text-n7">
                {f.dtTime(run.created_at)} · {stats.length ? stats.join(' · ') : '—'}
              </div>
              {run.error && <div className="col-span-2 break-words text-[13px] text-danger">{run.error}</div>}
            </div>
          )
        })
      )}
    </div>
  )
}
