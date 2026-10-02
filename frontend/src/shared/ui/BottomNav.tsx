import { Link } from '@tanstack/react-router'
import type { LucideIcon } from 'lucide-react'
import { telegram } from '@/shared/lib/telegram'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  badge?: number
}

/** Pastki suzuvchi pill-navigatsiya. Blur faqat shu yerda (DESIGN_SYSTEM.md §6). */
export function BottomNav({ items }: { items: ReadonlyArray<NavItem> }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-[max(12px,env(safe-area-inset-bottom))]">
      <ul className="glass flex w-full max-w-md items-stretch justify-between rounded-full border border-border p-1.5">
        {items.map(({ to, label, icon: Icon, badge }) => (
          <li key={to} className="flex-1">
            <Link
              to={to}
              onClick={() => telegram.haptic.select()}
              activeOptions={{ exact: to === '/' }}
              className="group relative flex h-12 flex-col items-center justify-center gap-1 rounded-full text-text-3 transition-colors duration-200 data-[status=active]:text-accent-text"
            >
              <Icon size={20} strokeWidth={2} />
              <span className="font-mono text-[8px] font-medium uppercase tracking-[0.18em]">{label}</span>
              <span className="absolute bottom-0.5 size-1 rounded-full bg-accent opacity-0 transition-opacity group-data-[status=active]:opacity-100" />
              {badge ? (
                <span className="tnum absolute right-[18%] top-1 grid h-4 min-w-4 place-items-center rounded-full bg-accent px-1 font-mono text-[9px] font-medium text-accent-ink">
                  {badge}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}
