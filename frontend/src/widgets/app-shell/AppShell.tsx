import { useQuery } from '@tanstack/react-query'
import { Outlet } from '@tanstack/react-router'
import { BookOpen, ClipboardList, FilePen, LayoutGrid, PackageCheck, RefreshCw, UserRound, UsersRound, Wallet } from 'lucide-react'
import { meQuery, useActiveRole, type Role } from '@/entities/user'
import { useI18n, type Messages } from '@/shared/i18n'
import { BottomNav, type NavItem } from '@/shared/ui'

type NavKey = 'home' | 'requests' | 'orders' | 'catalog' | 'receiving' | 'finance' | 'users' | 'iiko' | 'profile'

const ITEMS: Record<NavKey, Omit<NavItem, 'label'>> = {
  home: { to: '/', icon: LayoutGrid },
  requests: { to: '/requests', icon: FilePen },
  orders: { to: '/orders', icon: ClipboardList },
  catalog: { to: '/catalog', icon: BookOpen },
  receiving: { to: '/receiving', icon: PackageCheck },
  finance: { to: '/finance', icon: Wallet },
  users: { to: '/admin/users', icon: UsersRound },
  iiko: { to: '/admin/iiko', icon: RefreshCw },
  profile: { to: '/profile', icon: UserRound },
}

/**
 * BottomNav faol rolga qarab (DESIGN_SYSTEM.md §7). Hozircha faqat mavjud sahifalar;
 * zayavkalar, to'lovlar, nazorat ekranlari tegishli bosqichlarda qo'shiladi.
 */
const NAV_BY_ROLE: Record<Role, ReadonlyArray<NavKey>> = {
  initiator: ['home', 'requests', 'catalog', 'profile'],
  buyer: ['home', 'requests', 'orders', 'catalog', 'profile'],
  approver: ['home', 'requests', 'orders', 'finance', 'profile'],
  storekeeper: ['home', 'receiving', 'profile'],
  accountant: ['home', 'finance', 'orders', 'catalog', 'profile'],
  auditor: ['home', 'requests', 'orders', 'receiving', 'finance', 'profile'],
  // 6 tadan ortig'i telefonda sig'maydi: iiko sinxroni — profil sahifasidan
  admin: ['home', 'requests', 'finance', 'catalog', 'users', 'profile'],
}

const buildNav = (role: Role | null, t: Messages): NavItem[] =>
  (role ? NAV_BY_ROLE[role] : (['home', 'profile'] as const)).map((key) => ({ ...ITEMS[key], label: t.nav[key] }))

export function AppShell() {
  const { t } = useI18n()
  const { data: me } = useQuery(meQuery)
  const role = useActiveRole(me)

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
      <BottomNav items={buildNav(role, t)} />
    </div>
  )
}
