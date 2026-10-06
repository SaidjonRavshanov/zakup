/**
 * Ustki qatlamlar komponentlari: pastdan chiqadigan panel (sheet), tasdiqlash oynasi, toast va sahifa amallari paneli.
 * Holat va chaqiriladigan funksiyalar — overlay-state.ts (confirmAction, toast, usePageActions).
 */
import { Check as CheckIcon, X } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { actionsStore, confirmStore, toastStore } from './overlay-state'
import { Btn, Corners } from './primitives'

interface SheetProps {
  open: boolean
  title: ReactNode
  onClose: () => void
  children: ReactNode
}

/** Pastki panel: fon bosilsa, × yoki Esc — yopiladi. */
export function Sheet({ open, title, onClose, children }: SheetProps) {
  const closeRef = useRef(onClose)
  useEffect(() => {
    closeRef.current = onClose
  })
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeRef.current()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  if (!open) return null
  return createPortal(
    <div
      onClick={onClose}
      className="fixed inset-0 z-40 flex flex-col items-center justify-end"
      style={{ background: 'color-mix(in srgb, var(--color-neutral-900) 45%, transparent)', animation: 'zkFade .15s ease-out' }}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[84dvh] w-full max-w-[560px] flex-col border-t border-line bg-ground text-ink"
        style={{ animation: 'zkUp .2s ease-out', paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex shrink-0 items-center gap-3 pb-2 pl-4 pr-2 pt-3">
          <div className="flex-1 font-head text-[22px] leading-tight" style={{ fontWeight: 600 }}>
            {title}
          </div>
          <button type="button" onClick={onClose} aria-label="×" className="grid size-11 place-items-center text-ink">
            <X size={20} />
          </button>
        </div>
        <div className="overflow-y-auto px-4 pb-6">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

export function ConfirmHost() {
  const req = confirmStore.use()
  if (!req) return null
  const done = (ok: boolean) => {
    confirmStore.set(null)
    req.resolve(ok)
  }
  return createPortal(
    <div
      className="fixed inset-0 z-50 grid place-items-center p-6"
      style={{ background: 'color-mix(in srgb, var(--color-neutral-900) 50%, transparent)', animation: 'zkFade .15s ease-out' }}
    >
      <div role="alertdialog" aria-modal="true" className="dialog blueprint bg-ground text-ink">
        <Corners />
        <div className="dialog-title">{req.title}</div>
        {req.body && <div className="dialog-body">{req.body}</div>}
        <div className="dialog-actions">
          <Btn onClick={() => done(false)}>{req.cancel}</Btn>
          <Btn variant="primary" danger={req.danger} onClick={() => done(true)}>
            {req.label}
          </Btn>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export function ToastHost() {
  const t = toastStore.use()
  if (!t) return null
  return createPortal(
    <div
      key={t.id}
      role="status"
      className="fixed left-1/2 top-3 z-[60] flex w-max max-w-[90%] -translate-x-1/2 items-center gap-2 bg-ink px-3.5 py-2.5 text-[14px] text-ground"
      style={{ boxShadow: 'var(--shadow-md)', animation: 'zkFade .15s ease-out', marginTop: 'env(safe-area-inset-top)' }}
    >
      <CheckIcon size={20} />
      <span>{t.text}</span>
    </div>,
    document.body,
  )
}

/** Pastki panel: ikkinchi amal chapda, asosiy (blueprint) — o'ngda; telefonda keng. */
export function ActionBar({ wide }: { wide: boolean }) {
  const { primary: p, secondary: s } = actionsStore.use()
  if (!p && !s) return null
  return (
    <div className="flex shrink-0 justify-end gap-2.5 border-t border-line bg-ground px-4 pb-3.5 pt-3">
      {s && (
        <Btn
          size="lg"
          danger={s.danger}
          disabled={s.disabled}
          loading={s.loading}
          onClick={s.onClick}
          style={{ flex: p ? '0 1 auto' : '1' }}
        >
          {s.label}
        </Btn>
      )}
      {p && (
        <Btn
          variant="primary"
          size="lg"
          danger={p.danger}
          disabled={p.disabled}
          loading={p.loading}
          onClick={p.onClick}
          style={{ flex: '1 1 auto', maxWidth: wide ? 360 : 'none' }}
        >
          {p.label}
        </Btn>
      )}
    </div>
  )
}
