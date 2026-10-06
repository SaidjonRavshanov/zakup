# Redesign: Industry (Claude Design prototype)

Source of truth: `../../design/Zakup Prototype.dc.html` (markup lines 85–975, logic `vm*` 980–1260).
Prototype is served at http://127.0.0.1:8099/Zakup%20Prototype.dc.html. Mock data is `../../design/zakup-data.js` (reference only — use real APIs).

## Rules
- Keep ALL existing behaviour: API calls, mutations, query invalidation, permissions, offline receiving, validations. Only the UI changes.
- Do NOT import from `@/shared/ui` (old design, will be deleted). Use `@/shared/kit` + Tailwind utilities.
- Strings: `const { z, f, locale } = useZk()` from `@/shared/i18n/use-zk`. `z` has every prototype key (`src/shared/i18n/zk.ts`; `window.ZKI` keys in prototype `t.xxx` → `z.xxx`). Templates: `fill(z.cf_cancel_req, { id })`.
  If a string is missing, add it in a page-local file `src/pages/<group>/i18n.ts`: `export const L = { ru: {...}, uz: {...} }` and use `L[locale].key`. Do NOT edit `zk.ts` (other agents work in parallel).
  The old `useI18n().t` may still be used for strings not in zk (e.g. server error messages), but prefer zk.
- Formatting (`f`): `f.money(x)` "262 000 сум", `f.cmp(x)` "184,2 млн", `f.qty(v, unit)`, `f.unit(code)`, `f.pack(code)`, `f.n(x)`, `f.dt(iso)` Сегодня/Завтра/4 окт, `f.dtTime(iso)`, `f.time(iso)`, `f.pct(x)`.
- Statuses: `status(z, 'request'|'order'|'receipt'|'iiko'|'payment'|'invoice'|'job', value)` → `{label, tone}` → `<Tag tone={s.tone}>{s.label}</Tag>`.
- Main actions of a screen go to the sticky bottom bar: `usePageActions({ primary: {label, onClick, disabled, loading}, secondary: {label, onClick, danger} })` (prototype `vmX().primary/secondary`). Do not render these buttons inline.
- Confirm irreversible actions: `if (await confirmAction({ title, body: z.cf_irrev, label, cancel: z.a_cancel, danger: true })) ...`. Success feedback: `toast(z.toast_xxx)`.
- Back navigation is automatic (Telegram BackButton / desktop "Назад"). Don't render back buttons. Bottom nav is only on root sections.
- Phone first (width 360–430), but desktop ≥1024 must look good (content max 1040px for lists, 720px detail). Tables on desktop for finance debts / analytics suppliers (`table` class) — prototype shows them.
- Icons: lucide-react, size 20 (inline) / 22 (nav). Stroke is 1.5 globally.
- Tailwind colors: `bg-ground text-ink border-line text-n7 bg-n2 bg-a1 text-a7 text-a8 bg-acc text-warn bg-warnbg text-danger bg-dangerbg`; font `font-head` (Barlow Condensed — always with `style={{fontWeight:600}}`). Arbitrary sizes like `text-[15px]` match the prototype.
- Square corners everywhere. No rounded, no shadows on cards. Hairline `border-line`.

## Kit (`@/shared/kit`)
- `Blueprint` (frame with + corners, `onClick` makes it a button), `Corners`
- `Btn` variant primary|secondary|ghost, size sm|md|lg, icon, block, danger, loading
- `Tag tone` neutral|accent|solid|ok|warn|danger
- `Seg options=[{value,label,count}] value onChange scroll size` — filters/tabs; `Chips` — wrapping chip selectors (multi: value array)
- `PageHead title kicker sub aside` — h1 34px
- `Section aside` — 13px label with margin-top 24px
- `Row meta title sub amount badge badgeTop lead onClick` — list row 72px; `LinkRow` — related doc link
- `Cells items=[{label,value,color}] cols size` — KPI grid; `KV rows=[[k,v]]`; `TotalLine label value`
- `Banner tone=warn|danger|info icon action onClose onClick`; `Empty title hint`; `Skeleton`, `RowsSkeleton n`
- `Field label hint error`, `Input invalid`, `Textarea`, `SearchInput value onChange`, `Stepper value(string) onChange step unit size`, `Check on onToggle`, `Switch on`, `DropZone icon title hint onClick`
- `Sheet open title onClose` (bottom sheet, max 560)
- `confirmAction`, `toast`, `usePageActions`
- `src/shared/lib/telegram.ts` for haptics; `src/shared/offline/outbox.ts` for offline receipts.

## Checks
`npx tsc -b` and `npm run lint` must be clean for your files. Do not run `npm run build`/dev server (other agents). Do not touch files outside your group except where stated.
