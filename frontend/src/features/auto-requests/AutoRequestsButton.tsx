import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { RefreshCw, X } from 'lucide-react'
import { REQUESTS_KEY, requestsApi, type AutoSkipReason } from '@/entities/purchase-request'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk, type ZkKey } from '@/shared/i18n/use-zk'
import { Banner, Blueprint, Btn, toast } from '@/shared/kit'

const SKIP_KEY: Record<AutoSkipReason, ZkKey> = {
  already_today: 'skip_today',
  in_open_request: 'skip_inreq',
  no_offer: 'skip_nosup',
  no_history: 'skip_nohist',
  enough_stock: 'skip_enough',
}

/** Avto-zayavkani qo'lda ishga tushirish (har ertalab worker o'zi ham tuzadi) + natija bloki. */
export function AutoRequestsButton() {
  const { z } = useZk()
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const run = useMutation({
    mutationFn: () => requestsApi.runAuto(),
    onSuccess: async () => {
      toast(z.toast_auto)
      await queryClient.invalidateQueries({ queryKey: REQUESTS_KEY })
    },
  })
  const result = run.data
  const skipped = result
    ? (Object.entries(result.skipped) as Array<[AutoSkipReason, number]>).filter(([, n]) => n > 0)
    : []

  return (
    <>
      <Btn size="lg" block className="mt-4" icon={<RefreshCw size={20} />} loading={run.isPending} onClick={() => run.mutate()}>
        {z.a_auto}
      </Btn>
      {result && (
        <Blueprint className="mt-4 px-4 py-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="text-[16px] font-medium">
              {`${z.auto_created}: ${result.request_ids.length} · ${z.auto_lines}: ${result.lines}`}
            </div>
            <button type="button" aria-label="×" onClick={() => run.reset()} className="grid size-8 place-items-center text-n7">
              <X size={20} />
            </button>
          </div>
          {result.request_ids.length === 0 && <div className="mt-1 text-[14px] text-n7">{z.auto_none}</div>}
          {result.request_ids.map((id, i) => (
            <Btn
              key={id}
              variant="primary"
              block
              className="mt-2.5"
              onClick={() => navigate({ to: '/requests/$requestId', params: { requestId: id } })}
            >
              {result.request_ids.length > 1 ? `${z.open_auto} ${i + 1}` : z.open_auto}
            </Btn>
          ))}
          {skipped.length > 0 && (
            <>
              <div className="mb-1 mt-1.5 text-[13px] text-n7">{z.skipped}</div>
              {skipped.map(([reason, n]) => (
                <div key={reason} className="flex justify-between border-b border-dashed border-line py-1 text-[14px]">
                  <span>{z[SKIP_KEY[reason]]}</span>
                  <span>{n}</span>
                </div>
              ))}
            </>
          )}
        </Blueprint>
      )}
      {run.error && (
        <Banner tone="danger" onClose={() => run.reset()}>
          {describeError(run.error, t)}
        </Banner>
      )}
    </>
  )
}
