import { useRouter } from '@tanstack/react-router'
import { Row, Tag } from '@/shared/kit'
import type { TodoItem } from './use-todo'

/** Vazifalar qatorlari: chapda tepada yorliq, o'ngda summa + strelka. */
export function TodoList({ items }: { items: TodoItem[] }) {
  const router = useRouter()
  return (
    <div>
      {items.map((x) => (
        <Row
          key={x.key}
          badgeTop
          badge={<Tag tone={x.tone}>{x.label}</Tag>}
          title={x.title}
          sub={x.meta}
          amount={x.amount}
          onClick={() => router.history.push(x.href)}
        />
      ))}
    </div>
  )
}
