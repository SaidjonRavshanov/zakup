/** Barcha vazifalar (prototip "todo", vmTodo): "Требует действия" va "Сегодня" guruhlari + oy ko'rsatkichlari. */
import { useQuery } from '@tanstack/react-query'
import { summaryQuery } from '@/entities/analytics'
import { TodoList, useTodo } from '@/features/todo'
import { useZk } from '@/shared/i18n/use-zk'
import { Cells, Empty, PageHead, RowsSkeleton, Section } from '@/shared/kit'

const FULL = ['buyer', 'approver', 'accountant', 'auditor', 'admin']

export default function TodoPage() {
  const { z, f } = useZk()
  const { items, role, loading } = useTodo()
  const full = role !== null && FULL.includes(role)
  const { data: summary } = useQuery({ ...summaryQuery, enabled: full })
  const groups = [
    { key: 'now', title: z.g_now, items: items.filter((x) => x.group === 'now') },
    { key: 'today', title: z.g_today, items: items.filter((x) => x.group === 'today') },
  ].filter((g) => g.items.length)

  return (
    <div>
      <PageHead title={z.inbox} sub={`${f.cnt(items.length, 'tasks_n')}${role ? ` · ${z[`r_${role}`]}` : ''}`} />
      {loading && !items.length && <RowsSkeleton n={4} />}
      {groups.map((g) => (
        <div key={g.key}>
          <Section>{g.title}</Section>
          <TodoList items={g.items} />
        </div>
      ))}
      {!loading && !items.length && <Empty title={z.no_tasks} hint={z.no_tasks_hint} />}
      {full && summary && (
        <>
          <Section className="mb-2 mt-7">{z.month_kpi}</Section>
          <Cells
            items={[
              { label: z.month_buy, value: f.cmp(summary.purchases) },
              { label: z.kp_pending, value: summary.pending_requests },
              { label: z.kp_debt, value: f.cmp(summary.debt) },
              { label: z.kp_overdue, value: f.cmp(summary.overdue), color: Number(summary.overdue) > 0 ? 'var(--zk-danger)' : undefined },
            ]}
          />
        </>
      )}
    </div>
  )
}
