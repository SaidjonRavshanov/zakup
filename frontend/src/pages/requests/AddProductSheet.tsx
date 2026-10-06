import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Info } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { productQuery, productsQuery, type Offer, type ProductListItem } from '@/entities/catalog'
import { fill, useZk } from '@/shared/i18n/use-zk'
import { Banner, Btn, SearchInput, Sheet, Stepper } from '@/shared/kit'
import { packInfo, parseQty, qtyStep } from './labels'

export interface PickedProduct {
  product: ProductListItem
  qty: string
  /** Narx ko'rsatish uchun (eng arzon faol taklif); zayavkaga backend o'zi tanlaydi. */
  offer: Offer | null
}

/**
 * "Добавить товар": qidiruv (≥2 belgi, 8 natija) → miqdor stepperi + qadoqqa yaxlitlash izohi.
 * Qo'shilgandan keyin holatni tozalash uchun sahifa `key` ni o'zgartiradi.
 */
export function AddProductSheet({
  open,
  onClose,
  exclude,
  onAdd,
  busy,
  error,
}: {
  open: boolean
  onClose: () => void
  exclude: ReadonlySet<string>
  onAdd: (picked: PickedProduct) => void
  busy?: boolean
  error?: string | null
}) {
  const { z, f } = useZk()
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim())
  const [picked, setPicked] = useState<ProductListItem | null>(null)
  const [qty, setQty] = useState('1')
  const { data: products = [], isFetching } = useQuery({ ...productsQuery(query), enabled: open && query.length >= 2 })
  const { data: detail } = useQuery({ ...productQuery(picked?.id ?? ''), enabled: !!picked })
  const results = query.length >= 2 ? products.filter((p) => !exclude.has(p.id) && !p.archived).slice(0, 8) : []

  const offers = (detail?.offers ?? []).filter((o) => !o.archived)
  const offer = offers.length ? offers.reduce((a, b) => (Number(b.base_unit_price) < Number(a.base_unit_price) ? b : a)) : null
  const value = parseQty(qty)
  const ok = !!picked && value > 0

  const close = () => {
    setSearch('')
    setPicked(null)
    setQty('1')
    onClose()
  }

  let hint = ''
  let warn = false
  if (picked && detail) {
    if (!offer) {
      hint = z.no_offer
      warn = true
    } else if (value > 0) {
      const pk = packInfo(value, offer, f, picked.base_unit)
      const head = pk.label
        ? pk.round
          ? fill(z.round_hint, { q: f.qty(value, picked.base_unit), p: pk.label })
          : `= ${pk.label}`
        : f.qty(value, picked.base_unit)
      hint = `${head} · ${offer.supplier_name} · ${f.money(pk.sum)}`
      warn = pk.round
    }
  }

  return (
    <Sheet open={open} title={z.add_item} onClose={close}>
      {!picked ? (
        <>
          <SearchInput value={search} onChange={setSearch} placeholder={z.search_prod} autoFocus />
          {query.length < 2 ? (
            <div className="py-3 text-[14px] text-n7">{z.search_hint}</div>
          ) : (
            !isFetching && results.length === 0 && <div className="py-3 text-[14px] text-n7">{z.nothing_found}</div>
          )}
          {results.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setPicked(p)
                setQty('1')
              }}
              className="zk-hover flex min-h-14 w-full items-center gap-3 border-b border-line py-2 text-left text-ink"
            >
              <div className="min-w-0 flex-1">
                <div className="text-[16px] font-medium">{p.name}</div>
                <div className="text-[13px] text-n7">
                  {[p.article, p.category_name, f.unit(p.base_unit)].filter(Boolean).join(' · ')}
                </div>
              </div>
              <ChevronRight size={20} />
            </button>
          ))}
        </>
      ) : (
        <>
          <div className="flex items-center gap-3 border-b border-line pb-3 pt-2">
            <div className="flex-1 text-[17px] font-medium">{picked.name}</div>
            <Btn variant="ghost" size="sm" onClick={() => setPicked(null)}>
              {z.a_change}
            </Btn>
          </div>
          <div className="mb-2 mt-4 text-[13px] font-medium text-n7">{`${z.qty} · ${f.unit(picked.base_unit)}`}</div>
          <Stepper size={56} value={qty} onChange={setQty} step={qtyStep(picked.base_unit)} label={z.qty} />
          {hint && (
            <div
              className="mt-2.5 flex items-start gap-2 px-3 py-2.5 text-[14px]"
              style={
                warn
                  ? { background: 'var(--zk-warn-bg)', color: 'var(--zk-warn)' }
                  : { background: 'var(--color-accent-100)', color: 'var(--color-accent-800)' }
              }
            >
              <Info size={20} className="shrink-0" />
              <span>{hint}</span>
            </div>
          )}
          {error && <Banner tone="danger">{error}</Banner>}
          <Btn
            variant="primary"
            size="lg"
            block
            className="mt-4"
            disabled={!ok}
            loading={busy}
            onClick={() => {
              if (!picked || !ok) return
              onAdd({ product: picked, qty, offer })
            }}
          >
            {z.a_add}
          </Btn>
        </>
      )}
    </Sheet>
  )
}
