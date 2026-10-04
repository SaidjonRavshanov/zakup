/** Kichik chiziqli grafik (kutubxonasiz): narx dinamikasi uchun. Nuqtalar sana bo'yicha tartiblangan bo'lishi kerak. */
export function Sparkline({ values, height = 56, className }: { values: number[]; height?: number; className?: string }) {
  if (values.length < 2) return null
  const width = 300
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - 4 - ((v - min) / span) * (height - 8)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  const rising = values[values.length - 1]! > values[0]!
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className={className} style={{ height }} aria-hidden>
      <polyline
        points={points.join(' ')}
        fill="none"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
        className={rising ? 'stroke-danger' : 'stroke-accent'}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
