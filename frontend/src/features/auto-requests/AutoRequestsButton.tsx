import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { REQUESTS_KEY, requestsApi, type AutoRunResult, type AutoSkipReason } from '@/entities/purchase-request'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { FormError, LaserButton } from '@/shared/ui'

/** Avto-zayavkani qo'lda ishga tushirish (har ertalab worker o'zi ham tuzadi). */
export function AutoRequestsButton() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const run = useMutation({
    mutationFn: () => requestsApi.runAuto(),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      await queryClient.invalidateQueries({ queryKey: REQUESTS_KEY })
    },
  })
  return (
    <div className="mb-4">
      <LaserButton variant="ghost" block icon={<Sparkles size={14} />} loading={run.isPending} onClick={() => run.mutate()}>
        {t.requests.auto.run}
      </LaserButton>
      {run.data && <p className="mt-2 text-center text-[12px] text-text-2">{summary(run.data, t)}</p>}
      <FormError>{run.error && describeError(run.error, t)}</FormError>
    </div>
  )
}

function summary(result: AutoRunResult, t: ReturnType<typeof useI18n>['t']): string {
  const head = result.request_ids.length
    ? t.requests.auto.created(result.request_ids.length, result.lines)
    : t.requests.auto.nothing
  const reasons = (Object.entries(result.skipped) as Array<[AutoSkipReason, number]>)
    .filter(([, n]) => n > 0)
    .map(([reason, n]) => `${t.requests.auto.skipped[reason]}: ${n}`)
  return reasons.length ? `${head} · ${reasons.join(', ')}` : head
}
