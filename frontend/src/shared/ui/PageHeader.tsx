import type { ReactNode } from 'react'
import { MonoLabel } from './MonoLabel'

interface PageHeaderProps {
  meta: string
  title: string
  action?: ReactNode
}

/** Sahifa sarlavhasi: mono kontekst (ombor / rol) + og'ir display sarlavha. */
export function PageHeader({ meta, title, action }: PageHeaderProps) {
  return (
    <header className="flex items-end justify-between gap-4 pb-5 pt-4">
      <div className="min-w-0">
        <MonoLabel className="mb-3">{meta}</MonoLabel>
        <h1 className="truncate font-display text-[34px] font-extrabold uppercase leading-[0.9] tracking-[-0.05em]">{title}</h1>
      </div>
      {action}
    </header>
  )
}
