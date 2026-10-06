/** Narx dinamikasi (kutubxonasiz, prototip `chart()`): accent chiziq + kvadrat nuqtalar, ingichka ramka. */
export function Sparkline({ values, height = 96, className }: { values: number[]; height?: number; className?: string }) {
  if (values.length < 2) return null
  const width = 320
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const points = values.map((v, i) => [(i * (width - 12)) / (values.length - 1) + 6, height - 10 - ((v - min) / span) * (height - 20)] as const)
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      className={className}
      style={{ display: 'block', border: '1px solid var(--color-divider)' }}
      aria-hidden
    >
      <polyline points={points.map((p) => p.join(',')).join(' ')} fill="none" stroke="var(--color-accent)" strokeWidth={1.5} />
      {points.map(([x, y], i) => (
        <rect key={i} x={x - 3} y={y - 3} width={6} height={6} fill="var(--color-bg)" stroke="var(--color-accent)" strokeWidth={1.5} />
      ))}
    </svg>
  )
}
