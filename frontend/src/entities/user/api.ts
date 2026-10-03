import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type { Grant, User } from './model'

export type UserStatusFilter = 'pending' | 'active'

export const meQuery = queryOptions({
  queryKey: ['me'],
  queryFn: ({ signal }) => apiRequest<User>('/me', { signal }),
  staleTime: 5 * 60_000,
})

export const usersQuery = queryOptions({
  queryKey: ['identity', 'users'],
  queryFn: ({ signal }) => apiRequest<User[]>('/identity/users?limit=200', { signal }),
})

export const changeMyLocale = (locale: User['locale']) => apiRequest<void>('/me', { method: 'PATCH', body: { locale } })

export const activateUser = (id: string) => apiRequest<void>(`/identity/users/${id}/activate`, { method: 'POST' })

export const deactivateUser = (id: string) => apiRequest<void>(`/identity/users/${id}/deactivate`, { method: 'POST' })

export const setUserRoles = (id: string, grants: Grant[]) =>
  apiRequest<void>(`/identity/users/${id}/roles`, { method: 'PUT', body: { grants } })
