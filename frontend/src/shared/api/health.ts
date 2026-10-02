import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from './client'

export interface HealthDto {
  status: 'ok' | 'degraded'
  database: 'ok' | 'down'
  version: string
}

export const healthQuery = queryOptions({
  queryKey: ['health'],
  queryFn: ({ signal }) => apiRequest<HealthDto>('/health', { signal }),
  refetchInterval: 30_000,
  retry: false,
})
