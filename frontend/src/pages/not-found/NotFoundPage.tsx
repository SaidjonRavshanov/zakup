import { useZk } from '@/shared/i18n/use-zk'
import { Empty } from '@/shared/kit'

export function NotFoundPage() {
  const { z } = useZk()
  return <Empty className="py-16" title={z.not_found} hint={z.not_found_hint} />
}
