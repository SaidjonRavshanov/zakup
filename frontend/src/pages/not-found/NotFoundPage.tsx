import { useI18n } from '@/shared/i18n'
import { EmptyState } from '@/shared/ui'

export function NotFoundPage() {
  const { t } = useI18n()
  return <EmptyState code="404" title={t.common.pageNotFound} />
}
