import { Plus } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { LanguageSwitch } from '@/features/language-switch'
import { ThemeSwitch } from '@/features/theme-switch'
import { useI18n } from '@/shared/i18n'
import {
  ActorStack,
  Card,
  Countdown,
  DiffIndicator,
  EmptyState,
  LaserButton,
  MonoLabel,
  MoneyText,
  PageHeader,
  QtyStepper,
  QtyText,
  SearchPill,
  SegmentedControl,
  Skeleton,
  StatTile,
  StatusBadge,
} from '@/shared/ui'

function Section({ code, children }: { code: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <MonoLabel className="mb-3">{code}</MonoLabel>
      {children}
    </section>
  )
}

const inMinutes = (m: number) => new Date(Date.now() + m * 60_000).toISOString()

/** Faqat dev build: dizayn tizimi vitrini (DESIGN_SYSTEM.md §8). Komponent nomlari — kod identifikatorlari. */
export default function DevUiPage() {
  const { t } = useI18n()
  const [qty, setQty] = useState(10.5)
  const [tab, setTab] = useState<'a' | 'b' | 'c'>('a')

  return (
    <div>
      <PageHeader meta={t.devUi.meta} title={t.devUi.title} />
      <div className="flex flex-col gap-2">
        <LanguageSwitch />
        <ThemeSwitch />
      </div>

      <Section code="01/LaserButton">
        <div className="flex flex-wrap gap-2">
          <LaserButton icon={<Plus size={14} />}>{t.devUi.approve}</LaserButton>
          <LaserButton variant="ghost">{t.devUi.returnBack}</LaserButton>
          <LaserButton variant="danger">{t.devUi.reject}</LaserButton>
          <LaserButton loading>{t.devUi.sending}</LaserButton>
          <LaserButton disabled>{t.devUi.disabled}</LaserButton>
        </div>
      </Section>

      <Section code="02/StatusBadge">
        <div className="flex flex-wrap gap-2">
          <StatusBadge>{t.poStatus.CREATED}</StatusBadge>
          <StatusBadge tone="accent">{t.poStatus.CONFIRMED}</StatusBadge>
          <StatusBadge tone="info">{t.poStatus.SENT}</StatusBadge>
          <StatusBadge tone="warning">{t.poStatus.REAPPROVAL}</StatusBadge>
          <StatusBadge tone="danger">{t.poStatus.CANCELLED}</StatusBadge>
        </div>
      </Section>

      <Section code="03/Card + Bento">
        <div className="grid grid-cols-2 gap-3">
          <Card index="01/Card" title={t.devUi.cardTitle} interactive className="col-span-2">
            <p className="mt-2 text-sm text-text-2">{t.devUi.cardText}</p>
          </Card>
          <StatTile label={t.dashboard.pendingApproval} value="3" unit={t.dashboard.pcs} />
          <StatTile label={t.dashboard.savings} value="1,8" unit={t.dashboard.mln} delta={4.2} deltaGoodWhen="up" />
        </div>
      </Section>

      <Section code="04/Countdown">
        <div className="flex gap-6">
          <Countdown until={inMinutes(185)} className="text-3xl" />
          <Countdown until={inMinutes(42)} className="text-3xl" />
          <Countdown until={inMinutes(-15)} className="text-3xl" />
        </div>
      </Section>

      <Section code="05/ActorStack">
        <ActorStack
          actors={[
            { id: '1', name: 'Aziz Karimov', done: true },
            { id: '2', name: 'Dilnoza Rahimova', done: true },
            { id: '3', name: 'Bobur Aliyev', done: false },
            { id: '4', name: 'Kamola Yusupova', done: false },
          ]}
        />
      </Section>

      <Section code="06/SearchPill + Segmented">
        <SearchPill placeholder={t.devUi.search} />
        <SegmentedControl
          className="mt-3"
          value={tab}
          onChange={setTab}
          segments={[
            { value: 'a', label: t.orders.filters.all, count: 12 },
            { value: 'b', label: t.orders.filters.in_transit, count: 4 },
            { value: 'c', label: t.devUi.closed },
          ]}
        />
      </Section>

      <Section code="07/Qty + Diff + Money">
        <QtyStepper value={qty} onChange={setQty} step={0.5} unit={t.units.kg} label={t.devUi.quantity} />
        <div className="mt-3 flex flex-wrap items-center gap-4">
          <DiffIndicator expected={10} actual={qty} unit={t.units.kg} tolerancePct={3} />
          <QtyText value={qty} unit={t.units.kg} />
          <MoneyText value={1_250_000} />
        </div>
      </Section>

      <Section code="08/Skeleton + Empty">
        <Skeleton className="h-[76px]" />
        <EmptyState code="404" title={t.common.notFound} description={t.devUi.emptyHint} />
      </Section>

      <Section code="09/Typography">
        <div className="font-display text-5xl font-extrabold uppercase leading-[0.9] tracking-[-0.05em]">Zakup Закуп</div>
        <p className="mt-3 text-text-2">{t.devUi.typographySample}</p>
        <MonoLabel className="mt-3">Geist Mono · {t.receiving.invoicePhoto} · 0123456789</MonoLabel>
      </Section>
    </div>
  )
}
