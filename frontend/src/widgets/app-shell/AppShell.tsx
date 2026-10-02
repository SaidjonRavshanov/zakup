import { Outlet } from '@tanstack/react-router'
import { ClipboardList, LayoutGrid, PackageCheck, UserRound } from 'lucide-react'
import { useI18n } from '@/shared/i18n'
import { BottomNav, type NavItem } from '@/shared/ui'

export function AppShell() {
  const { t } = useI18n()
  // TODO(identity): rolga qarab element ro'yxati (DESIGN_SYSTEM.md §7)
  const nav: ReadonlyArray<NavItem> = [
    { to: '/', label: t.nav.home, icon: LayoutGrid },
    { to: '/orders', label: t.nav.orders, icon: ClipboardList, badge: 2 },
    { to: '/receiving', label: t.nav.receiving, icon: PackageCheck },
    { to: '/profile', label: t.nav.profile, icon: UserRound },
  ]

  return (
    <div className="relative mx-auto min-h-dvh max-w-xl">
      {/* Fon atmosferasi: bitta statik glow (animatsiyasiz) */}
      <div
        aria-hidden
        className="glow pointer-events-none fixed -left-32 -top-40 -z-10 size-[420px] rounded-full bg-[radial-gradient(circle,var(--glow-ambient),transparent_65%)]"
      />
      <main className="px-4 pb-32 pt-[max(8px,env(safe-area-inset-top))]">
        <Outlet />
      </main>
      <BottomNav items={nav} />
    </div>
  )
}
