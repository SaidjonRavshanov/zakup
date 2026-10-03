import { useQuery, useQueryClient } from '@tanstack/react-query'
import { LogIn, LogOut, RefreshCw } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { meQuery, userRoles } from '@/entities/user'
import { LanguageSwitch } from '@/features/language-switch'
import { devSignIn, ensureSession, forgetDevIdentity, rememberedDevIdentity } from '@/shared/api/auth'
import { ApiError } from '@/shared/api/client'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { EmptyState, LaserButton, MonoLabel, Skeleton } from '@/shared/ui'

/**
 * Ilovaga kirish nazorati: sessiya → /me → kamida bitta rol.
 * Faqat shundan keyin router (sahifalar) chiziladi.
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
    <div className="mx-auto grid min-h-dvh max-w-md place-items-center px-4 py-10 animate-[enter_0.5s_var(--ease-expo)_both]">
      <div className="w-full">{children}</div>
    </div>
  )
}

function Loading() {
  const { t } = useI18n()
  return (
    <Screen>
      <MonoLabel className="mb-4 text-center">{t.auth.checking}</MonoLabel>
      <Skeleton className="h-[76px]" />
    </Screen>
  )
}

function PendingScreen({ onRetry }: { onRetry: () => void }) {
  const { t } = useI18n()
  const telegramId = telegram.userId() ?? rememberedDevIdentity()?.telegram_id ?? null
  return (
    <Screen>
      <EmptyState
        code="403 · PENDING"
        title={t.auth.pendingTitle}
        description={t.auth.pendingText}
        action={
          <div className="flex flex-col items-center gap-5">
            {telegramId && (
              <div className="text-center">
                <MonoLabel>{t.auth.yourId}</MonoLabel>
                <div className="tnum mt-2 select-all font-mono text-2xl font-medium">{telegramId}</div>
              </div>
            )}
            <LaserButton variant="ghost" icon={<RefreshCw size={14} />} onClick={onRetry}>
              {t.auth.checkAgain}
            </LaserButton>
            {import.meta.env.DEV && !telegram.userId() && (
              <button
                className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-3"
                onClick={() => {
                  forgetDevIdentity()
                  onRetry()
                }}
              >
                <LogOut size={12} className="mr-2 inline" />
                {t.auth.signOut}
              </button>
            )}
          </div>
        }
      />
      <LanguageSwitch className="mt-4" />
    </Screen>
  )
}

function NoRolesScreen({ onRetry }: { onRetry: () => void }) {
  const { t } = useI18n()
  return (
    <Screen>
      <EmptyState
        code="NO ROLE"
        title={t.auth.noRolesTitle}
        description={t.auth.noRolesText}
        action={
          <LaserButton variant="ghost" icon={<RefreshCw size={14} />} onClick={onRetry}>
            {t.auth.checkAgain}
          </LaserButton>
        }
      />
    </Screen>
  )
}

function OpenInTelegram() {
  const { t } = useI18n()
  return (
    <Screen>
      <EmptyState code="401" title={t.auth.openInTelegram} description={t.auth.openInTelegramText} />
    </Screen>
  )
}

function FailedScreen({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { t } = useI18n()
  return (
    <Screen>
      <EmptyState
        code={error instanceof ApiError ? String(error.status) : 'ERR'}
        title={t.auth.failed}
        description={describeError(error, t)}
        action={
          <LaserButton variant="ghost" icon={<RefreshCw size={14} />} onClick={onRetry}>
            {t.common.retry}
          </LaserButton>
        }
      />
    </Screen>
  )
}

const inputClass =
  'h-12 w-full rounded-full border border-border-soft bg-surface-2 px-5 font-mono text-[13px] tracking-[0.04em] text-text outline-none transition-colors duration-300 focus:border-[var(--accent-border)]'

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
      <MonoLabel className="mb-3">{`DEV · ${t.profile.browserDev}`}</MonoLabel>
      <h1 className="font-display text-[34px] font-extrabold uppercase leading-[0.9] tracking-[-0.05em]">{t.auth.devTitle}</h1>
      <p className="mt-3 text-sm text-text-2">{t.auth.devHint}</p>
      <form onSubmit={submit} className="mt-6 flex flex-col gap-3">
        <label className="flex flex-col gap-2">
          <MonoLabel>{t.auth.devId}</MonoLabel>
          <input
            className={inputClass}
            inputMode="numeric"
            pattern="[0-9]+"
            required
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value.replace(/\D/g, ''))}
          />
        </label>
        <label className="flex flex-col gap-2">
          <MonoLabel>{t.auth.devName}</MonoLabel>
          <input className={inputClass} maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        {failure && <p className="text-sm text-danger">{failure}</p>}
        <LaserButton type="submit" size="lg" block loading={busy} disabled={!telegramId} icon={<LogIn size={16} />} className="mt-2">
          {t.auth.signIn}
        </LaserButton>
      </form>
    </Screen>
  )
}

