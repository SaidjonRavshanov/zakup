import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent, type ReactNode } from 'react'
import { meQuery, userRoles } from '@/entities/user'
import { LanguageSwitch } from '@/features/language-switch'
import { devSignIn, ensureSession, forgetDevIdentity, rememberedDevIdentity } from '@/shared/api/auth'
import { ApiError } from '@/shared/api/client'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Btn, Corners, Field, Input, Skeleton } from '@/shared/kit'
import { telegram } from '@/shared/lib/telegram'

/**
 * Ilovaga kirish nazorati: sessiya → /me → kamida bitta rol.
 * Faqat shundan keyin router (sahifalar) chiziladi. Ko'rinish — prototip "login".
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const sessionState = useQuery({ queryKey: ['session'], queryFn: ensureSession, staleTime: Infinity, retry: false })
  const me = useQuery({ ...meQuery, enabled: sessionState.data === true, retry: false })

  const restart = () => {
    queryClient.removeQueries({ queryKey: ['me'] })
    void queryClient.resetQueries({ queryKey: ['session'] })
  }

  const error = sessionState.error ?? me.error
  if (error instanceof ApiError && error.code === 'account_pending') return <PendingScreen onRetry={restart} />
  if (sessionState.data === false || (error instanceof ApiError && error.status === 401)) {
    return import.meta.env.DEV ? <DevSignIn onDone={restart} /> : <OpenInTelegram />
  }
  if (error) return <FailedScreen error={error} onRetry={restart} />
  if (!me.data) return <Loading />
  if (userRoles(me.data).length === 0) return <NoRolesScreen onRetry={restart} />
  return children
}

function Screen({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-ground px-2 py-6 text-center text-ink">
      <div className="font-head text-[40px] leading-none" style={{ fontWeight: 600 }}>
        Zakup
      </div>
      {children}
      <LanguageSwitch size="sm" className="mt-3" />
    </div>
  )
}

const Text = ({ children }: { children: ReactNode }) => <div className="max-w-[300px] text-[16px]">{children}</div>

function Retry({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <Btn variant="primary" size="lg" className="min-w-[220px]" onClick={onClick}>
      {label}
    </Btn>
  )
}

function Loading() {
  const { z } = useZk()
  return (
    <Screen>
      <div className="text-[16px] text-n7">{z.login_checking}</div>
      <div className="flex w-[220px] flex-col gap-2">
        <Skeleton className="h-3" />
        <Skeleton className="h-3 w-[70%]" />
      </div>
    </Screen>
  )
}

function PendingScreen({ onRetry }: { onRetry: () => void }) {
  const { t } = useI18n()
  const { z } = useZk()
  const telegramId = telegram.userId() ?? rememberedDevIdentity()?.telegram_id ?? null
  return (
    <Screen>
      <Text>{z.login_pending}</Text>
      {telegramId && (
        <div className="blueprint select-all px-5 py-3">
          <Corners />
          <div className="text-[13px] text-n7">{z.your_tg_id}</div>
          <div className="font-head text-[34px] tracking-[0.02em]" style={{ fontWeight: 600 }}>
            {telegramId}
          </div>
        </div>
      )}
      <Retry onClick={onRetry} label={z.a_check_again} />
      {import.meta.env.DEV && !telegram.userId() && (
        <Btn
          variant="ghost"
          onClick={() => {
            forgetDevIdentity()
            onRetry()
          }}
        >
          {t.auth.signOut}
        </Btn>
      )}
    </Screen>
  )
}

function NoRolesScreen({ onRetry }: { onRetry: () => void }) {
  const { z } = useZk()
  return (
    <Screen>
      <Text>{z.login_norole}</Text>
      <Retry onClick={onRetry} label={z.a_check_again} />
    </Screen>
  )
}

function OpenInTelegram() {
  const { z } = useZk()
  return (
    <Screen>
      <Text>{z.login_notg}</Text>
    </Screen>
  )
}

function FailedScreen({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { t } = useI18n()
  const { z } = useZk()
  return (
    <Screen>
      {error instanceof ApiError && <div className="text-[14px] text-danger">{error.code}</div>}
      <Text>{z.login_error}</Text>
      <div className="max-w-[300px] text-[14px] text-n7">{describeError(error, t)}</div>
      <Retry onClick={onRetry} label={z.a_retry} />
    </Screen>
  )
}

/** Faqat dev build: Telegram'siz brauzerda kirish (backend ZAKUP_DEV_AUTH_BYPASS=true bo'lsa). */
function DevSignIn({ onDone }: { onDone: () => void }) {
  const { t } = useI18n()
  const [telegramId, setTelegramId] = useState(() => String(rememberedDevIdentity()?.telegram_id ?? ''))
  const [name, setName] = useState(() => rememberedDevIdentity()?.first_name ?? 'Dev')
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setFailure(null)
    try {
      await devSignIn({ telegram_id: Number(telegramId), first_name: name.trim() || 'Dev' })
      onDone()
    } catch (error) {
      if (error instanceof ApiError && error.code === 'account_pending') onDone()
      else setFailure(describeError(error, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen>
      <Text>{t.auth.devTitle}</Text>
      <div className="max-w-[320px] text-[13px] text-n7">{t.auth.devHint}</div>
      <form onSubmit={submit} className="flex w-full max-w-[320px] flex-col gap-3 text-left">
        <Field label={t.auth.devId}>
          <Input
            inputMode="numeric"
            pattern="[0-9]+"
            required
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value.replace(/\D/g, ''))}
          />
        </Field>
        <Field label={t.auth.devName}>
          <Input maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        {failure && <div className="text-[14px] text-danger">{failure}</div>}
        <Btn type="submit" variant="primary" size="lg" block loading={busy} disabled={!telegramId}>
          {t.auth.signIn}
        </Btn>
      </form>
    </Screen>
  )
}
