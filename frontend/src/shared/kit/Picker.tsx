/**
 * Ko'p variantli tanlov (o'nlab ombor): 8 tagacha — chiplar, ko'p bo'lsa — tanlangani bitta qatorda,
 * bosilganda qidiruvli pastki panel.
 */
import { Check as CheckIcon, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Sheet } from './overlays'
import { Chips, SearchInput } from './primitives'

export interface PickerOption {
  value: string
  label: string
  sub?: string | null
}

interface PickerProps {
  options: ReadonlyArray<PickerOption>
  value: string
  onChange: (value: string) => void
  title: string
  searchPlaceholder?: string
  /** Shundan ko'p bo'lsa — panel; aks holda chiplar. */
  chipsUpTo?: number
}

export function Picker({ options, value, onChange, title, searchPlaceholder, chipsUpTo = 8 }: PickerProps) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')

  if (options.length <= chipsUpTo) {
    return (
      <Chips
        options={options.map((o) => ({ value: o.value, label: o.sub ? `${o.label} · ${o.sub}` : o.label }))}
        value={value}
        onChange={onChange}
      />
    )
  }

  const current = options.find((o) => o.value === value)
  const query = q.trim().toLowerCase()
  const visible = query
    ? options.filter((o) => `${o.label} ${o.sub ?? ''}`.toLowerCase().includes(query))
    : options

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="zk-hover flex min-h-12 w-full items-center gap-3 border border-line px-3.5 text-left text-ink"
      >
        <div className="min-w-0 flex-1">
          <div className="truncate text-[16px] font-medium">{current?.label ?? '—'}</div>
          {current?.sub && <div className="truncate text-[13px] text-n7">{current.sub}</div>}
        </div>
        <ChevronDown size={20} />
      </button>
      <Sheet
        open={open}
        title={title}
        onClose={() => {
          setOpen(false)
          setQ('')
        }}
      >
        <SearchInput value={q} onChange={setQ} placeholder={searchPlaceholder} />
        <div className="mt-2">
          {visible.map((o) => {
            const on = o.value === value
            return (
              <button
                key={o.value}
                type="button"
                onClick={() => {
                  onChange(o.value)
                  setOpen(false)
                  setQ('')
                }}
                className="zk-hover flex min-h-[52px] w-full items-center gap-3 border-b border-line text-left text-ink"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-[16px]" style={{ fontWeight: on ? 500 : 400 }}>
                    {o.label}
                  </div>
                  {o.sub && <div className="text-[13px] text-n7">{o.sub}</div>}
                </div>
                {on && <CheckIcon size={20} className="text-a7" />}
              </button>
            )
          })}
        </div>
      </Sheet>
    </>
  )
}
