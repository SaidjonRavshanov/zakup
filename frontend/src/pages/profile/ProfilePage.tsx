/** Profil (prototip "profile", vmProfile): rol chiplari, omborlar, til, mavzu, admin uchun iiko kartasi. */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ChevronRight, RefreshCw } from 'lucide-react'
import { storesQuery } from '@/entities/catalog'
import { changeMyLocale, meQuery, setActiveRole, useActiveRole, useHasRole, userRoles } from '@/entities/user'
import { LanguageSwitch } from '@/features/language-switch'
import { ThemeSwitch } from '@/features/theme-switch'
import { forgetDevIdentity, signOut } from '@/shared/api/auth'
import { useZk } from '@/shared/i18n/use-zk'
import { Blueprint, Btn, Chips, KV, RowsSkeleton, Section, toast } from '@/shared/kit'
import { isInTelegram } from '@/shared/lib/telegram'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { z } = useZk()
  const queryClient = useQueryClient()
  const { data: me } = useQuery(meQuery)
  const { data: stores } = useQuery(storesQuery)
  const role = useActiveRole(me)
  const isAdmin = useHasRole('admin')

  if (!me) return <RowsSkeleton n={4} />

  const roles = userRoles(me)
  const scoped = me.grants.filter((g) => g.store_id !== null).map((g) => g.store_id as string)
  const allStores = me.grants.some((g) => g.store_id === null)
  const storeNames = allStores
    ? z.all_stores
    : [...new Set(scoped)].map((id) => stores?.find((s) => s.id === id)?.name ?? '…').join(', ')

  const exit = async () => {
    await signOut().catch(() => undefined)
    forgetDevIdentity()
    queryClient.clear()
    window.location.reload()
  }

  return (
    <div>
      <div className="pt-2">
        <h1 className="m-0 text-[32px]">{me.full_name}</h1>
        <div className="text-[14px] text-n7">
          {me.username ? `@${me.username} · ` : ''}Telegram ID {me.telegram_id}
        </div>
      </div>

      <Section className="mb-2 mt-5">{roles.length > 1 ? z.active_role : z.roles}</Section>
      {role && (
        <Chips
          value={role}
          options={roles.map((r) => ({ value: r, label: z[`r_${r}`] }))}
          onChange={(r) => {
            if (r === role) return
            setActiveRole(r)
            toast(`${z.toast_role}: ${z[`r_${r}`]}`)
          }}
        />
      )}

      <KV
        className="mt-4"
        rows={[
          [z.stores_l, storeNames],
          [z.opened_in, isInTelegram ? 'Telegram' : z.browser],
        ]}
      />

      <Section className="mb-2 mt-5">{z.language}</Section>
      {/* Bot xabarlari va PDF ham shu tilda bo'lishi uchun backend'ga saqlanadi */}
      <LanguageSwitch onChange={(locale) => void changeMyLocale(locale).catch(() => undefined)} />
      <div className="mt-1.5 text-[13px] text-n7">{z.lang_note}</div>

      <Section className="mb-2 mt-5">{z.theme}</Section>
      <ThemeSwitch />

      {isAdmin && (
        <Blueprint className="mt-6 flex items-center gap-3 p-4" onClick={() => navigate({ to: '/admin/iiko' })}>
          <span className="text-a7">
            <RefreshCw size={24} />
          </span>
          <div className="flex-1">
            <div className="font-head text-[20px]" style={{ fontWeight: 600 }}>
              {z.iiko_sync}
            </div>
            <div className="text-[14px] text-n7">{z.ik_ref} · {z.ik_prices} · {z.ik_stock} · {z.ik_usage}</div>
          </div>
          <ChevronRight size={20} />
        </Blueprint>
      )}

      {!isInTelegram && (
        <Btn size="lg" block className="mt-6" onClick={() => void exit()}>
          {z.logout}
        </Btn>
      )}
    </div>
  )
}
