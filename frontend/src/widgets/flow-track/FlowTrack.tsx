import { useZk } from '@/shared/i18n/use-zk'
import { STEPS, type Flow } from './flow'

export function FlowTrack({ flow, className = '' }: { flow: Flow; className?: string }) {
  const { z } = useZk()
  const color = (i: number) => {
    if (i < flow.at) return 'var(--color-accent)'
    if (i > flow.at) return 'var(--color-divider)'
    return flow.mark === 'stop' ? 'var(--zk-danger)' : flow.mark === 'warn' ? 'var(--zk-warn)' : 'var(--color-accent)'
  }
  return (
    <div className={`mt-4 ${className}`}>
      <ol className="m-0 grid list-none grid-cols-5 gap-1 p-0" aria-label={z.fl_title}>
        {STEPS.map((key, i) => {
          const current = i === flow.at
          return (
            <li key={key} className="min-w-0" aria-current={current ? 'step' : undefined}>
              <div className="h-1.5" style={{ background: color(i) }} />
              <div
                className="mt-1.5 truncate text-[12px] leading-tight"
                style={{ color: current ? color(i) : i < flow.at ? 'var(--color-ink)' : 'var(--color-neutral-700)', fontWeight: current ? 600 : 400 }}
              >
                {z[key]}
              </div>
            </li>
          )
        })}
      </ol>
      <div className="mt-2 text-[14px] leading-snug">
        <span className="font-medium">{`${z.fl_now}: `}</span>
        {flow.hint}
      </div>
    </div>
  )
}
