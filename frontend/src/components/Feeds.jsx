import { Link } from 'react-router-dom'
import EventIcon, { eventSentence } from './EventIcon'
import { cx } from './ui'
import { SEVERITY_STYLE, article, dayTime, who } from '../lib/format'

const isFresh = (row) => row._fresh && Date.now() - row._fresh < 2500
const KIND_LABEL = { INDICATOR: 'Indicator', ANOMALY: 'AI anomaly' }

/** One incident: severity dot, title, who · articles · time, and the score. Details live on the incident page. */
export function IncidentRow({ incident }) {
  const s = SEVERITY_STYLE[incident.severity] || SEVERITY_STYLE.LOW
  return (
    <Link to={`/incidents/${incident.id}`}
      className={cx('group grid grid-cols-[auto_1fr_auto] items-center gap-4 border-b border-line px-5 py-3.5 last:border-0 hover:bg-panel-2',
        isFresh(incident) && 'flash')}>
      <span className={cx('h-2.5 w-2.5 rounded-full', s.dot)} />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink group-hover:text-accent">{incident.title}</p>
        <p className="mt-0.5 truncate text-xs text-ink-3">
          {who(incident)}
          <span className="mx-1.5">·</span>
          {incident.articles.slice(0, 3).map(article).join(', ')}
          {KIND_LABEL[incident.kind] && <><span className="mx-1.5">·</span>{KIND_LABEL[incident.kind]}</>}
        </p>
      </div>
      <div className="text-right">
        <p className={cx('tabular text-lg font-semibold leading-none', s.text)}>{incident.score}</p>
        <p className="tabular mt-1 text-[11px] text-ink-3">{dayTime(incident.detected_at)}</p>
      </div>
    </Link>
  )
}

/** One activity event as a sentence. Sensitive data and out-of-shift activity are marked, nothing else. */
export function EventRow({ event, highlight }) {
  const sensitive = event.sensitivity === 'HIGH'
  const notes = []
  if (event.category) notes.push(`${event.category.replace('_', ' ').toLowerCase()} data`)
  if (event.data_subject_name) notes.push(`subject ${event.data_subject_name}`)
  if (event.outside_shift) notes.push('outside shift')
  return (
    <div className={cx('flex items-start gap-3 border-b border-line px-5 py-3 last:border-0', isFresh(event) && 'flash',
      highlight && 'bg-accent/5')}>
      <EventIcon type={event.event_type} size={15} className={cx('mt-0.5 shrink-0', sensitive ? 'text-crit' : 'text-ink-3')} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-ink-2">
          <span className="font-medium text-ink">{event.employee?.full_name || event.account}</span> {eventSentence(event)}
        </p>
        {(notes.length > 0 || highlight) && (
          <p className={cx('mt-0.5 truncate text-xs', sensitive ? 'text-crit/80' : 'text-ink-3')}>
            {highlight && <span className="font-medium text-accent">evidence · </span>}{notes.join(' · ')}
          </p>
        )}
      </div>
      <span className="tabular shrink-0 text-[11px] text-ink-3">{dayTime(event.occurred_at)}</span>
    </div>
  )
}
