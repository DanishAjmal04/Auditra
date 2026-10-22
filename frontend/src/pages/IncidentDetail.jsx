import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, CircleSlash, Eye, FileWarning, Flag, Gavel, Link2, RotateCcw } from 'lucide-react'
import api, { errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useLive } from '../lib/live'
import { CATEGORIES, DAYS, SEVERITY_STYLE, STATUS_LABEL, article, full, time } from '../lib/format'
import { eventSentence } from '../components/EventIcon'
import { EventRow } from '../components/Feeds'
import { Button, Card, CardHeader, Empty, ErrorNote, Modal, Spinner, Textarea, cx } from '../components/ui'

const KIND_TEXT = { VIOLATION: 'Potential violation', INDICATOR: 'Risk indicator', ANOMALY: 'AI anomaly' }
const ACTIONS = [
  ['INVESTIGATE', 'Start investigation', Flag],
  ['ACKNOWLEDGE', 'Acknowledge', Eye],
  ['ESCALATE', 'Escalate to DPO', Gavel],
  ['RESOLVE', 'Resolve', CheckCircle2],
  ['FALSE_POSITIVE', 'False positive', CircleSlash],
]
const TIMELINE_PREVIEW = 8

function Row({ label, children }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-4 border-b border-line py-3 last:border-0">
      <dt className="text-sm text-ink-3">{label}</dt>
      <dd className="min-w-0 text-sm text-ink">{children}</dd>
    </div>
  )
}

function reasonOf(item) {
  return typeof item === 'string' ? { title: '', text: item, articles: [] } : item
}

export default function IncidentDetail() {
  const { id } = useParams()
  const { version } = useLive()
  const { isAdmin } = useAuth()
  const [incident, setIncident] = useState(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [showAll, setShowAll] = useState(false)

  const load = useCallback(() => api.get(`/incidents/${id}/`).then((r) => setIncident(r.data)).catch((e) => setError(errorText(e))), [id])
  useEffect(() => { load() }, [load, version])

  async function act() {
    setBusy(true)
    setError('')
    try {
      if (pending === 'REPORT_LOST_DEVICE') await api.post(`/incidents/${id}/report-lost-device/`, { note })
      else await api.post(`/incidents/${id}/act/`, { action: pending, note })
      setPending(null)
      setNote('')
      load()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  if (!incident) return error ? <ErrorNote>{error}</ErrorNote> : <Spinner />
  const s = SEVERITY_STYLE[incident.severity]
  const closed = ['RESOLVED', 'FALSE_POSITIVE'].includes(incident.status)
  const usbRelated = incident.rule_codes.some((c) => c.startsWith('usb'))
  const emp = incident.employee_detail
  const reasons = incident.reasons.map(reasonOf)
  const timeline = incident.timeline || []
  const shownTimeline = showAll ? timeline : timeline.slice(0, TIMELINE_PREVIEW)
  const total = incident.score_breakdown.reduce((sum, i) => sum + i.points, 0)

  return (
    <div className="mx-auto max-w-6xl">
      <Link to="/incidents" className="inline-flex items-center gap-1.5 text-sm text-ink-3 hover:text-ink"><ArrowLeft size={14} /> All incidents</Link>

      {/* Headline: what, how bad, where it stands */}
      <div className="mt-4 flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <p className={cx('flex items-center gap-2 text-xs font-semibold uppercase tracking-wider', s.text)}>
            <span className={cx('h-2 w-2 rounded-full', s.dot)} />{incident.severity} · {KIND_TEXT[incident.kind]}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">{incident.title}</h1>
          <p className="mt-1.5 text-sm text-ink-3">
            INC-{incident.number} · {full(incident.occurred_at)} · <span className="font-medium text-ink-2">{STATUS_LABEL[incident.status]}</span>
          </p>
        </div>
        <div className="text-right">
          <p className={cx('tabular text-5xl font-semibold leading-none tracking-tight', s.text)}>{incident.score}</p>
          <p className="mt-1.5 text-xs text-ink-3">risk score / 100</p>
        </div>
      </div>
      <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.7fr_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Summary" />
            <dl className="px-5">
              <Row label="Who">
                {emp ? (
                  <Link to={`/employees/${emp.id}`} className="font-medium text-accent hover:underline">{emp.full_name}</Link>
                ) : incident.account ? (
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[13px]">{incident.account}</span>
                    <span className="text-ink-3">not linked to an employee</span>
                    {isAdmin && <Link to="/admin/employees" className="inline-flex items-center gap-1 text-accent hover:underline"><Link2 size={13} />Link account</Link>}
                  </span>
                ) : <span className="text-ink-2">Organisation (from GDPR records)</span>}
                {emp && <span className="text-ink-3"> · {emp.role_label}, {emp.department}</span>}
              </Row>
              <Row label="What">
                {incident.events[0]
                  ? <>{eventSentence(incident.events[0])}{incident.events.length > 1 && <span className="text-ink-3"> and {incident.events.length - 1} more event(s)</span>} <span className="text-ink-3">at {time(incident.events[0].occurred_at)}</span></>
                  : incident.summary}
              </Row>
              {incident.data && (
                <Row label="Data">
                  {incident.data.name} · {CATEGORIES[incident.data.category]} · <span className={incident.data.sensitivity === 'HIGH' ? 'font-medium text-crit' : ''}>{incident.data.sensitivity}</span>
                  {incident.data.subject && <> · subject <Link to="/records?tab=subjects" className="text-accent hover:underline">{incident.data.subject}</Link></>}
                </Row>
              )}
              <Row label="GDPR">{incident.articles.map(article).join(', ')}</Row>
              {incident.machine && <Row label="Machine">{incident.machine}</Row>}
            </dl>
          </Card>

          <Card>
            <CardHeader title="Why it was flagged" subtitle={`${reasons.length} rule${reasons.length > 1 ? 's' : ''} matched`} />
            <ol className="divide-y divide-line">
              {reasons.map((r, i) => (
                <li key={i} className="flex gap-4 px-5 py-3.5">
                  <span className="tabular mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-panel-2 text-[11px] font-semibold text-ink-2">{i + 1}</span>
                  <div className="min-w-0">
                    {r.title && <p className="text-sm font-medium text-ink">{r.title}{r.articles?.length ? <span className="font-normal text-ink-3"> · {r.articles.map(article).join(', ')}</span> : null}</p>}
                    <p className="mt-0.5 text-sm text-ink-2">{r.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <CardHeader title="Evidence" subtitle="What the agent recorded on the machine" />
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] font-medium uppercase tracking-wider text-ink-3">
                    <th className="px-5 py-2.5 font-medium">Time</th><th className="px-5 py-2.5 font-medium">Action</th><th className="px-5 py-2.5 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {incident.events.map((e) => (
                    <tr key={e.id} className="border-b border-line last:border-0 align-top">
                      <td className="tabular whitespace-nowrap px-5 py-3 text-ink-2">{time(e.occurred_at)}</td>
                      <td className="px-5 py-3">
                        <p className="text-ink">{eventSentence(e)}</p>
                        {(e.details?.source_path || e.path) && <p className="mt-0.5 break-all font-mono text-[11px] text-ink-3">{e.details?.source_path || e.path}</p>}
                      </td>
                      <td className="px-5 py-3 text-xs text-ink-3">
                        {e.source}{e.source_event_id ? ` · event ${e.source_event_id}` : ''}
                        {e.process && <p className="mt-0.5 break-all font-mono text-[11px]">{e.process.split('\\').pop()}</p>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <CardHeader title="Activity around it" subtitle="30 minutes before and after · evidence is highlighted"
              actions={emp && <Link to={`/activity?employee=${emp.id}`} className="text-xs font-medium text-accent hover:underline">All activity</Link>} />
            {timeline.length ? shownTimeline.map((e) => <EventRow key={e.id} event={e} highlight={e.is_evidence} />) : <Empty title="No other activity" />}
            {timeline.length > TIMELINE_PREVIEW && (
              <button onClick={() => setShowAll((v) => !v)} className="w-full border-t border-line px-5 py-2.5 text-xs font-medium text-accent hover:bg-panel-2">
                {showAll ? 'Show less' : `Show all ${timeline.length} events`}
              </button>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Decision" actions={<span className="text-xs font-medium text-ink-2">{STATUS_LABEL[incident.status]}</span>} />
            <div className="space-y-2 px-5 py-4">
              {!closed ? ACTIONS.map(([key, label, Icon], i) => (
                <Button key={key} icon={Icon} className="w-full justify-start" variant={i === 0 ? 'primary' : 'secondary'}
                  onClick={() => { setPending(key); setNote('') }}>{label}</Button>
              )) : <Button icon={RotateCcw} className="w-full" onClick={() => setPending('REOPEN')}>Reopen</Button>}
              {usbRelated && <Button icon={FileWarning} variant="danger" className="w-full justify-start" onClick={() => setPending('REPORT_LOST_DEVICE')}>Report lost device</Button>}
            </div>
            {incident.actions.length > 0 && (
              <div className="border-t border-line px-5 py-3">
                <p className="mb-2 text-xs font-medium text-ink-3">History</p>
                <ul className="space-y-2.5">
                  {incident.actions.map((a) => (
                    <li key={a.id} className="text-sm">
                      <p><span className="font-medium text-ink">{a.actor}</span> <span className="text-ink-2">{a.action_label.toLowerCase()}</span></p>
                      {a.note && <p className="text-xs text-ink-2">{a.note}</p>}
                      <p className="tabular text-[11px] text-ink-3">{full(a.created_at)}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {incident.breaches?.length > 0 && (
              <div className="border-t border-line px-5 py-3 text-sm">
                <Link to="/records?tab=breaches" className="font-medium text-crit hover:underline">Breach record open</Link>
                <p className="text-xs text-ink-3">Authority notification due {full(incident.breaches[0].deadline)}</p>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Risk score" subtitle="Every point and its reason" />
            <ul className="px-5 py-2">
              {incident.score_breakdown.map((item, i) => (
                <li key={i} className="flex items-start justify-between gap-4 border-b border-line py-2.5 text-sm last:border-0">
                  <span className="text-ink-2">{item.label}</span>
                  <span className="tabular shrink-0 font-medium text-ink">+{item.points}</span>
                </li>
              ))}
            </ul>
            <div className="flex items-center justify-between border-t border-line px-5 py-3 text-sm">
              <span className="font-medium text-ink">Total{total > 100 ? ' (capped)' : ''}</span>
              <span className={cx('tabular text-base font-semibold', s.text)}>{incident.score}</span>
            </div>
            {incident.ai_score != null && (
              <div className="border-t border-line px-5 py-3 text-sm">
                <p className="text-ink-2">AI anomaly today: <span className={cx('tabular font-semibold', incident.ai_score >= 60 ? 'text-high' : 'text-ink')}>{Math.round(incident.ai_score)}</span> / 100
                  <span className="text-ink-3"> {incident.ai_score >= 60 ? '(unusual)' : '(normal)'}</span></p>
                {incident.ai_score >= 40 && <p className="mt-0.5 text-xs text-ink-3">{incident.ai_reason}</p>}
              </div>
            )}
            <details className="border-t border-line px-5 py-3 text-xs text-ink-3">
              <summary className="cursor-pointer font-medium text-ink-2">How scores are calculated</summary>
              <p className="mt-2 leading-relaxed">Base by rule severity (critical 70, high 55, medium 35, low 15), +5 per extra GDPR article
                (max 10), +10 outside shift, +10 special-category or national-ID data, up to +15 when the AI score is above 60,
                +10 Art. 83 escalation after 3 violations in 7 days. Capped at 100.</p>
            </details>
          </Card>

          {emp && (
            <Card>
              <CardHeader title={emp.full_name} subtitle={`${emp.role_label} · ${emp.department}`}
                actions={<Link to={`/employees/${emp.id}`} className="text-xs font-medium text-accent hover:underline">Profile</Link>} />
              <dl className="px-5">
                <Row label="Shift">{emp.shift_start.slice(0, 5)}–{emp.shift_end.slice(0, 5)}, {emp.work_days.map((d) => DAYS[d]).join(' ')}</Row>
                <Row label="May access">up to {emp.max_sensitivity}</Row>
                <Row label="Categories">{emp.allowed_categories.length ? emp.allowed_categories.map((c) => CATEGORIES[c]).join(', ') : 'General only'}</Row>
              </dl>
            </Card>
          )}
        </div>
      </div>

      <Modal open={Boolean(pending)} onClose={() => setPending(null)}
        title={pending === 'REPORT_LOST_DEVICE' ? 'Report lost device' : ACTIONS.find(([k]) => k === pending)?.[1] || 'Reopen'}
        subtitle={pending === 'REPORT_LOST_DEVICE' ? 'Opens a breach record and starts the 72-hour Art. 33 clock.' : `INC-${incident.number} · ${incident.title}`}
        footer={<><Button variant="ghost" onClick={() => setPending(null)}>Cancel</Button><Button variant="primary" loading={busy} onClick={act}>Confirm</Button></>}>
        <Textarea autoFocus placeholder={['RESOLVE', 'FALSE_POSITIVE'].includes(pending) ? 'Required: explain the decision' : 'Note (optional)'}
          value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="mt-3"><ErrorNote>{error}</ErrorNote></div>
      </Modal>
    </div>
  )
}
