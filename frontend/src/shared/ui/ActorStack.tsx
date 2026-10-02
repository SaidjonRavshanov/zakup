import { cn } from '@/shared/lib/cn'

export interface Actor {
  id: string
  name: string
  /** Zanjirdagi bosqich bajarilganmi (masalan, tasdiqlangan). */
  done: boolean
}

const initials = (name: string) =>
  name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()

/** Zanjir ishtirokchilari: tashabbuskor → tasdiqlovchi → qabul qiluvchi... */
export function ActorStack({ actors, className }: { actors: Actor[]; className?: string }) {
  return (
    <div className={cn('flex items-center', className)}>
      {actors.slice(0, 5).map((actor, i) => (
        <span
          key={actor.id}
          title={actor.name}
          style={{ zIndex: 10 - i }}
          className={cn(
            'grid size-8 place-items-center rounded-full border-2 bg-surface-2 font-mono text-[10px] font-medium',
            i > 0 && '-ml-2',
            actor.done
              ? 'border-accent text-text shadow-[0_0_10px_var(--accent-glow)]'
              : 'border-dashed border-border text-text-3',
          )}
        >
          {initials(actor.name)}
        </span>
      ))}
    </div>
  )
}
