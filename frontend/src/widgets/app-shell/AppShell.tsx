/**
 * Ilova qobig'i (prototip: "Меню + Ещё"). Telefonda — pastki menyu faqat bo'lim sahifalarida (5 tadan ko'p
 * bo'lsa 4 ta + "Ещё"), ichki sahifada — Telegram "Назад". Desktop (≥1024px) — chap menyu 232px.
 * Sahifa asosiy amallarini `usePageActions` bilan e'lon qiladi — pastki qotirilgan panelda chiqadi.
 */
import { useQuery } from '@tanstack/react-query'
import { Outlet, useRouter, useRouterState } from '@tanstack/react-router'
import { ChevronLeft, Ellipsis } from 'lucide-react'
import { useEffect, useState, useSyncExternalStore } from 'react'
import { meQuery, useActiveRole } from '@/entities/user'
import { useTodo } from '@/features/todo'
import { useZk } from '@/shared/i18n/use-zk'
import { ActionBar, Btn, ConfirmHost, Sheet, ToastHost } from '@/shared/kit'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import { MENU, NAV, isRootPath, isWidePath, sectionOf, type NavKey } from './nav'

const DESKTOP = '(min-width: 1024px)'

function useDesktop(): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(DESKTOP)
      mq.addEventListener('change', cb)
      return () => mq.removeEventListener('change', cb)
    },
    () => window.matchMedia(DESKTOP).matches,
  )
}

export function AppShell() {
  const { z } = useZk()
  const router = useRouter()
  const path = useRouterState({ select: (s) => s.location.pathname })
  const { data: me } = useQuery(meQuery)
  const role = useActiveRole(me)
  const { items: todo } = useTodo()
  const desktop = useDesktop()
  const [moreOpen, setMoreOpen] = useState(false)

  const menu: NavKey[] = role ? MENU[role] : ['home', 'profile']
  const root = isRootPath(path)
  const section = sectionOf(path)
  const go = (to: string) => {
    setMoreOpen(false)
    router.history.push(to)
  }
  const back = () => {
    // Havola orqali to'g'ridan-to'g'ri ochilgan bo'lsa — tarix yo'q: bo'limga qaytamiz
    if (window.history.state?.idx > 0 || window.history.length > 1) router.history.back()
    else router.history.push(section)
  }

  // Telegram BackButton — faqat ichki sahifalarda
  useEffect(() => (root ? telegram.backButton(null) : telegram.backButton(back)))
  useEffect(() => window.scrollTo(0, 0), [path])

  const phoneItems: Array<NavKey | 'more'> = menu.length > 5 ? [...menu.slice(0, 4), 'more'] : menu
  const moreItems = menu.length > 5 ? menu.slice(4) : []
  const count = (k: NavKey) => (k === 'home' ? todo.length : 0)

  return (
    <div className="min-h-dvh bg-ground text-ink lg:pl-[232px]">
      {desktop && (
        <aside className="fixed inset-y-0 left-0 z-20 flex w-[232px] flex-col gap-0.5 overflow-y-auto border-r border-line px-3 py-5">
          <div className="px-2.5 pb-[18px]">
            <div className="font-head text-[28px] leading-none" style={{ fontWeight: 600 }}>
              Zakup
            </div>
            <div className="text-[13px] text-n7">Tarnov</div>
          </div>
          {menu.map((k) => {
            const item = NAV[k]
            const on = section === item.to
            const n = count(k)
            return (
              <button
                key={k}
                type="button"
                onClick={() => go(item.to)}
                className="zk-hover flex min-h-11 items-center gap-2.5 border-l-2 px-2.5 text-left text-[15px]"
                style={{
                  borderLeftColor: on ? 'var(--color-accent)' : 'transparent',
                  color: on ? 'var(--color-accent-700)' : 'var(--color-neutral-700)',
                }}
              >
                <item.icon size={22} />
                <span className="flex-1">{z[item.label]}</span>
                {n > 0 && <span className="text-[12px]">{n}</span>}
              </button>
            )
          })}
          <div className="mt-auto border-t border-line px-2.5 pt-3 text-[13px]">
            <div className="font-medium">{me?.full_name}</div>
            <div className="text-n7">{role ? z[`r_${role}`] : ''}</div>
          </div>
        </aside>
      )}

      <main
        className={cn(
          'mx-auto px-4 pb-7 pt-3 lg:px-8 lg:pb-12 lg:pt-6',
          desktop ? (isWidePath(path) ? 'max-w-[1104px]' : 'max-w-[784px]') : 'max-w-[640px]',
        )}
        style={{ paddingTop: desktop ? undefined : 'max(12px, env(safe-area-inset-top))' }}
      >
        {desktop && !root && (
          <Btn variant="ghost" size="sm" icon={<ChevronLeft size={20} />} onClick={back} className="mb-2">
            {z.back}
          </Btn>
        )}
        <Outlet />
      </main>

      <div className="sticky bottom-0 z-30" style={{ paddingBottom: 'env(safe-area-inset-bottom)', background: 'var(--color-bg)' }}>
        <div className={cn('mx-auto', desktop && (isWidePath(path) ? 'max-w-[1104px]' : 'max-w-[784px]'))}>
          <ActionBar wide={desktop} />
        </div>
        {!desktop && root && (
          <nav className="flex border-t border-line bg-ground">
            {phoneItems.map((k) => {
              const isMore = k === 'more'
              const Icon = isMore ? Ellipsis : NAV[k].icon
              const on = isMore ? moreItems.some((m) => NAV[m].to === section) : NAV[k].to === section
              const n = isMore ? 0 : count(k)
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => (isMore ? setMoreOpen(true) : go(NAV[k].to))}
                  className="relative -mt-px flex min-h-[58px] min-w-0 flex-[1_1_0] flex-col items-center justify-center gap-[3px] border-t-2 text-[12px]"
                  style={{
                    borderTopColor: on ? 'var(--color-accent)' : 'transparent',
                    color: on ? 'var(--color-accent-700)' : 'var(--color-neutral-700)',
                  }}
                >
                  <Icon size={22} />
                  <span className="max-w-full truncate px-0.5">{isMore ? z.more : z[NAV[k].label]}</span>
                  {n > 0 && (
                    <span className="absolute left-[calc(50%+6px)] top-[5px] h-[18px] min-w-[18px] bg-acc px-[5px] text-center text-[11px] leading-[18px] text-ground">
                      {n}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        )}
      </div>

      <Sheet open={moreOpen} title={z.more} onClose={() => setMoreOpen(false)}>
        {moreItems.map((k) => {
          const item = NAV[k]
          return (
            <button
              key={k}
              type="button"
              onClick={() => go(item.to)}
              className="zk-hover flex min-h-14 w-full items-center gap-3 border-b border-line text-left text-[17px]"
            >
              <item.icon size={22} />
              <span>{z[item.label]}</span>
            </button>
          )
        })}
      </Sheet>
      <ConfirmHost />
      <ToastHost />
    </div>
  )
}
