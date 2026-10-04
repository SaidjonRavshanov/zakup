import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'

export type SyncKind = 'references' | 'purchase_prices' | 'stock' | 'consumption'
export type SyncStatus = 'queued' | 'running' | 'done' | 'failed'

export interface IikoServer {
  code: string
  name: string
  department_code: string | null
}

export interface SyncRun {
  id: string
  server_code: string
  kind: SyncKind
  status: SyncStatus
  params: { days?: number }
  stats: Record<string, number>
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface SyncOverview {
  servers: IikoServer[]
  runs: SyncRun[]
}

const isActive = (run: SyncRun) => run.status === 'queued' || run.status === 'running'

export const iikoSyncQuery = queryOptions({
  queryKey: ['iiko', 'sync'],
  queryFn: ({ signal }) => apiRequest<SyncOverview>('/iiko/sync?limit=30', { signal }),
  // Navbatda / bajarilmoqda bo'lsa — tez-tez yangilaymiz (worker natijasini kutish)
  refetchInterval: (query) => (query.state.data?.runs.some(isActive) ? 3_000 : false),
})

export const requestIikoSync = (body: { server_code: string; kind: SyncKind; days?: number }) =>
  apiRequest<{ id: string }>('/iiko/sync', { method: 'POST', body })
