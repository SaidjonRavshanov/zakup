import { useQuery } from '@tanstack/react-query'
import { healthQuery } from '@/shared/api/health'
import { useI18n } from '@/shared/i18n'
import { StatusBadge } from '@/shared/ui'

/** Backend va DB holati — lokal sozlashda ulanishni tez tekshirish uchun. */
export function ApiStatus() {
  const { t } = useI18n()
  const { data, isPending, isError } = useQuery(healthQuery)
  if (isPending) return <StatusBadge>{t.apiStatus.checking}</StatusBadge>
  if (isError) return <StatusBadge tone="danger">{t.apiStatus.offline}</StatusBadge>
  return data.database === 'ok' ? (
    <StatusBadge tone="accent">{t.apiStatus.online(data.version)}</StatusBadge>
  ) : (
    <StatusBadge tone="warning">{t.apiStatus.dbDown}</StatusBadge>
  )
}
