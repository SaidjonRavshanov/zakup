/** "Нужно к": bugun / ertaga / indinga yoki istalgan sana (kalendar, 90 kungacha). */
import { useState } from 'react'
import { todayIso, useZk } from '@/shared/i18n/use-zk'
import { Input, Seg } from '@/shared/kit'

const OTHER = 'other'

export function NeedByPicker({ value, onChange }: { value: string; onChange: (date: string) => void }) {
  const { z, f } = useZk()
  const today = todayIso()
  const quick: string[] = [today, todayIso(1), todayIso(2)]
  const [custom, setCustom] = useState(!quick.includes(value))
  const options = [
    { value: today, label: z.today_l },
    { value: todayIso(1), label: z.tomorrow_l },
    { value: todayIso(2), label: f.dt(todayIso(2)) },
    { value: OTHER, label: custom && !quick.includes(value) ? f.dt(value) : z.other_date },
  ]
  return (
    <>
      <Seg
        options={options}
        value={custom ? OTHER : value}
        onChange={(v) => {
          if (v === OTHER) {
            setCustom(true)
            return
          }
          setCustom(false)
          onChange(v)
        }}
      />
      {custom && (
        <Input
          type="date"
          className="mt-2 w-full"
          aria-label={z.other_date}
          min={today}
          max={todayIso(90)}
          value={quick.includes(value) ? '' : value}
          onChange={(e) => e.target.value && e.target.value >= today && onChange(e.target.value)}
        />
      )}
    </>
  )
}
