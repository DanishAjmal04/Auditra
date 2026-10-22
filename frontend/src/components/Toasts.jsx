import { useNavigate } from 'react-router-dom'
import { ShieldAlert, X } from 'lucide-react'
import { useLive } from '../lib/live'
import { SEVERITY_STYLE, who } from '../lib/format'
import { Articles, cx } from './ui'

export default function Toasts() {
  const { toasts, dismiss } = useLive()
  const navigate = useNavigate()
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-40 flex w-96 flex-col gap-2">
      {toasts.map(({ id, incident }) => {
        const s = SEVERITY_STYLE[incident.severity] || SEVERITY_STYLE.LOW
        return (
          <div key={id}
            className={cx('slide-in pointer-events-auto cursor-pointer overflow-hidden rounded-xl border bg-panel shadow-2xl ring-1', s.ring, 'border-line-2')}
            onClick={() => { dismiss(id); navigate(`/incidents/${id}`) }}>
            <div className={cx('h-1', s.bar)} />
            <div className="flex gap-3 px-4 py-3">
              <ShieldAlert size={18} className={cx('mt-0.5 shrink-0', s.text)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={cx('text-[11px] font-bold tracking-wide', s.text)}>{incident.severity} · {incident.score}</span>
                  <span className="text-[11px] text-ink-3">INC-{incident.number}</span>
                </div>
                <p className="mt-0.5 text-sm font-semibold leading-snug">{incident.title}</p>
                <p className="mt-0.5 truncate text-xs text-ink-2">{who(incident)}</p>
                <div className="mt-1.5"><Articles items={incident.articles} max={5} /></div>
              </div>
              <button className="self-start rounded p-0.5 text-ink-3 hover:text-ink"
                onClick={(e) => { e.stopPropagation(); dismiss(id) }}><X size={14} /></button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
