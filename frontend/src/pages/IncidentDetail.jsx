import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, BrainCircuit, CheckCircle2, CircleSlash, Clock, Eye, FileWarning, Flag, Gavel, History, MessageSquare,
  RotateCcw, Scale, ShieldAlert, UserRound,
} from 'lucide-react'
import api, { errorText } from '../lib/api'
import { useLive } from '../lib/live'
import { CATEGORIES, DAYS, SEVERITY_STYLE, STATUS_LABEL, dayTime, full, who } from '../lib/format'
import EventIcon, { eventSentence } from '../components/EventIcon'
import { EventRow } from '../components/Feeds'
import {
  Articles, Button, Card, CardHeader, Empty, ErrorNote, Modal, PageHeader, Pill, SeverityBadge, Spinner, Textarea, cx,
} from '../components/ui'

const KIND_TEXT = { VIOLATION: 'potential violation', INDICATOR: 'risk indicator', ANOMALY: 'AI anomaly' }

const ACTIONS = [
  ['INVESTIGATE', 'Start investigation', Flag],
  ['ACKNOWLEDGE', 'Acknowledge', Eye],
  ['ESCALATE', 'Escalate to DPO', Gavel],
  ['RESOLVE', 'Resolve', CheckCircle2],
  ['FALSE_POSITIVE', 'False positive', CircleSlash],
]

function ScoreBreakdown({ incident }) {
  const s = SEVERITY_STYLE[incident.severity]
  const total = incident.score_breakdown.reduce((sum, i) => sum + i.points, 0)
  return (
    <Card>
      <CardHeader icon={Scale} title="How the score was built" subtitle="Every point is stored with its reason" />
      <div className="px-4 py-4">
        <div className="flex items-end gap-3">
          <span className={cx('tabular text-4xl font-semibold', s.text)}>{incident.score}</span>
          <span className="pb-1 text-sm text-ink-3">/ 100 · {incident.severity}</span>
        </div>
        <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-line">
          {incident.score_breakdown.map((item, i) => (
            <div key={i} className={cx('h-full border-r border-panel', i === 0 ? s.bar : 'bg-accent/70')}
              style={{ width: `${Math.min(100, item.points)}%`, opacity: i === 0 ? 1 : 0.55 + 0.45 / (i + 1) }} />
          ))}
        </div>
        <div className="mt-4 space-y-2">
          {incident.score_breakdown.map((item, i) => (
            <div key={i} className="flex items-start justify-between gap-4 text-sm">
              <span className="text-ink-2">{item.label}</span>
              <span className="tabular shrink-0 font-semibold text-ink">+{item.points}</span>
            </div>
          ))}
          {total > 100 && (
            <div className="flex justify-between text-xs text-ink-3"><span>Capped at 100</span><span className="tabular">{total} → 100</span></div>
          )}
        </div>
        <p className="mt-4 border-t border-line pt-3 text-[11px] leading-relaxed text-ink-3">
          Base by rule severity (CRITICAL 70, HIGH 55, MEDIUM 35, LOW 15), +5 per extra GDPR article (max 10), +10 outside
          shift, +10 special-category or national-ID data, up to +15 from an AI score above 60, +10 Art. 83 escalation
          after 3 violations in 7 days.
        </p>
      </div>
    </Card>
  )
}

function EvidenceChain({ incident }) {
  const first = incident.events[0]
  const steps = []
  if (first) {
    steps.push(['Windows recorded', `${first.source || 'Agent'}${first.source_event_id ? ` · event ${first.source_event_id}` : ''} on ${first.machine}`, first.event_type])
    steps.push(['Agent structured it', `${first.employee?.full_name || first.account} ${eventSentence(first)} at ${dayTime(first.occurred_at)}`, 'FILE_READ'])
    if (first.catalogue_name) {
      steps.push(['Catalogue matched', `${first.catalogue_name}: ${CATEGORIES[first.category] || first.category}, ${first.sensitivity} sensitivity${first.data_subject_name ? `, data subject ${first.data_subject_name}` : ''}`, 'RETENTION_EXCEEDED'])
    }
  }
  steps.push(['Rules matched', incident.rule_codes.join(', '), 'AUDIT_POLICY_CHANGED'])
  steps.push(['Scored', `${incident.score}/100 → ${incident.severity}`, 'TASK_CREATED'])
  return (
    <ol className="relative space-y-4 border-l border-line-2 pl-5">
      {steps.map(([title, text], i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[27px] flex h-5 w-5 items-center justify-center rounded-full border border-line-2 bg-panel-2 text-[10px] font-semibold text-ink-2">{i + 1}</span>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">{title}</p>
          <p className="mt-0.5 text-sm text-ink-2">{text}</p>
        </li>
      ))}
    </ol>
  )
}

export default function IncidentDetail() {
  const { id } = useParams()
  const { version } = useLive()
  const [incident, setIncident] = useState(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => api.get(`/incidents/${id}/`).then((r) => setIncident(r.data)).catch((e) => setError(errorText(e))), [id])
  useEffect(() => { load() }, [load, version])

  async function act() {
    setBusy(true)
    setError('')
    try {
      if (pending === 'REPORT_LOST_DEVICE') {
        await api.post(`/incidents/${id}/report-lost-device/`, { note })
      } else {
        await api.post(`/incidents/${id}/act/`, { action: pending, note })
      }
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
  const closed = ['RESOLVED', 'FALSE_POSITIVE'].includes(incident.status)
  const usbRelated = incident.rule_codes.some((c) => c.startsWith('usb'))
  const emp = incident.employee_detail
  const s = SEVERITY_STYLE[incident.severity]

  return (
    <>
      <Link to="/incidents" className="mb-3 inline-flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink"><ArrowLeft size={13} /> Incidents</Link>
      <PageHeader
        title={<span className="flex flex-wrap items-center gap-3">{incident.title}<SeverityBadge severity={incident.severity} /></span>}
        subtitle={`INC-${incident.number} · ${KIND_TEXT[incident.kind]} · detected ${full(incident.detected_at)}`}
      />
      <ErrorNote>{error}</ErrorNote>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <Card>
            <div className="px-6 py-5">
              <p className="text-xs font-medium uppercase tracking-wider text-ink-3">What happened</p>
              <p className="mt-2 text-base leading-relaxed text-ink">{incident.summary}</p>
              <p className="mt-3 text-sm text-ink-2"><span className="text-ink-3">GDPR </span><Articles items={incident.articles} max={8} /></p>
              {incident.reasons.length > 1 && (
                <>
                  <p className="mt-5 text-xs font-medium uppercase tracking-wider text-ink-3">Also matched</p>
                  <ul className="mt-2 space-y-2">
                    {incident.reasons.slice(1).map((reason, i) => (
                      <li key={i} className="flex gap-2.5 text-sm text-ink-2"><span className={cx('mt-2 h-1.5 w-1.5 shrink-0 rounded-full', s.dot)} />{reason}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader icon={ShieldAlert} title="Evidence" subtitle={`${incident.events.length} event(s) attached to this incident`} />
            <div className="grid gap-6 px-5 py-4 lg:grid-cols-[1fr_1.2fr]">
              <EvidenceChain incident={incident} />
              <div className="space-y-2">
                {incident.events.slice(0, 8).map((e) => (
                  <div key={e.id} className="rounded-lg border border-line bg-canvas/60 px-3 py-2 font-mono text-[11px] leading-relaxed text-ink-2">
                    <div className="mb-1 flex items-center gap-2 font-sans text-xs text-ink"><EventIcon type={e.event_type} /> {e.type_label}</div>
                    <p>time&nbsp;&nbsp;&nbsp;&nbsp;{full(e.occurred_at)}</p>
                    <p>account&nbsp;{e.account}</p>
                    {e.path && <p className="break-all">path&nbsp;&nbsp;&nbsp;&nbsp;{e.path}</p>}
                    {e.details?.source_path && <p className="break-all">source&nbsp;&nbsp;{e.details.source_path}</p>}
                    {e.process && <p className="break-all">process&nbsp;{e.process}</p>}
                    {e.device && <p>device&nbsp;&nbsp;{e.device}</p>}
                    {e.domain && <p>domain&nbsp;&nbsp;{e.domain}</p>}
                    {e.source_ip && <p>from&nbsp;&nbsp;&nbsp;&nbsp;{e.source_ip}</p>}
                  </div>
                ))}
                {incident.events.length > 8 && <p className="text-xs text-ink-3">+{incident.events.length - 8} more in the timeline</p>}
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader icon={Clock} title="Timeline" subtitle="Everything this person did 30 minutes before and after" />
            <div className="max-h-[480px] overflow-y-auto">
              {incident.timeline?.length ? incident.timeline.map((e) => <EventRow key={e.id} event={e} highlight={e.is_evidence} />)
                : <Empty title="No activity around this incident" />}
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <div className="px-5 py-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wider text-ink-3">Decision</p>
                <span className="text-sm font-medium text-ink">{STATUS_LABEL[incident.status]}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {!closed && ACTIONS.map(([key, label, Icon]) => (
                  <Button key={key} icon={Icon} variant={key === 'INVESTIGATE' ? 'primary' : key === 'ESCALATE' ? 'danger' : 'secondary'}
                    className={key === 'INVESTIGATE' ? 'col-span-2' : ''} onClick={() => { setPending(key); setNote('') }}>{label}</Button>
                ))}
                {closed && <Button icon={RotateCcw} className="col-span-2" onClick={() => setPending('REOPEN')}>Reopen</Button>}
                {usbRelated && <Button icon={FileWarning} variant="danger" className="col-span-2" onClick={() => setPending('REPORT_LOST_DEVICE')}>Report lost device (opens breach)</Button>}
              </div>
            </div>
          </Card>

          <ScoreBreakdown incident={incident} />

          {incident.ai_score != null && (
            <Card>
              <CardHeader icon={BrainCircuit} title="AI anomaly signal" subtitle="Employee-day compared with normal behaviour" />
              <div className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className={cx('tabular text-2xl font-semibold', incident.ai_score >= 60 ? 'text-high' : 'text-ink-2')}>{Math.round(incident.ai_score)}</span>
                  <span className="text-xs text-ink-3">/ 100 · alert line 60</span>
                </div>
                <p className="mt-2 text-sm text-ink-2">{incident.ai_reason}</p>
              </div>
            </Card>
          )}

          <Card>
            <CardHeader icon={UserRound} title={who(incident)} subtitle={incident.machine ? `on ${incident.machine}` : 'Organisation-level finding'}
              actions={emp && <Link to={`/employees/${emp.id}`} className="text-xs text-accent hover:underline">Profile</Link>} />
            {emp ? (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 px-4 py-3 text-sm">
                <dt className="text-ink-3">Role</dt><dd>{emp.role_label} · {emp.department}</dd>
                <dt className="text-ink-3">Type</dt><dd>{emp.employment_type === 'VENDOR' ? 'Vendor / processor' : 'Staff'}{emp.status === 'LEFT' && <Pill tone="crit" className="ml-2">Left</Pill>}</dd>
                <dt className="text-ink-3">Shift</dt><dd className="tabular">{emp.shift_start.slice(0, 5)}–{emp.shift_end.slice(0, 5)} · {emp.work_days.map((d) => DAYS[d]).join(' ')}</dd>
                <dt className="text-ink-3">May access</dt><dd>up to {emp.max_sensitivity}</dd>
                <dt className="text-ink-3">Categories</dt>
                <dd className="flex flex-wrap gap-1">{emp.allowed_categories.length ? emp.allowed_categories.map((c) => <Pill key={c}>{c}</Pill>) : <span className="text-ink-3">General only</span>}</dd>
              </dl>
            ) : (
              <p className="px-4 py-3 text-sm text-ink-3">
                {incident.account ? 'This Windows account is not linked to an employee, so it is treated as having no data permissions.' : 'Raised from GDPR records, not from one person.'}
              </p>
            )}
          </Card>

          {incident.breaches?.length > 0 && (
            <Card>
              <CardHeader icon={FileWarning} title="Breach record opened" />
              {incident.breaches.map((b) => (
                <div key={b.id} className="px-4 py-3 text-sm">
                  <p className="text-ink">{b.title}</p>
                  <p className="mt-1 text-xs text-ink-3">Authority notification due {full(b.deadline)} (Art. 33, 72 hours)</p>
                </div>
              ))}
            </Card>
          )}

          <Card>
            <CardHeader icon={History} title="Officer actions" />
            <div className="space-y-3 px-4 py-3">
              {incident.actions.length ? incident.actions.map((a) => (
                <div key={a.id} className="flex gap-3 text-sm">
                  <MessageSquare size={14} className="mt-0.5 shrink-0 text-ink-3" />
                  <div>
                    <p><span className="font-medium">{a.actor}</span> <span className="text-ink-2">{a.action_label.toLowerCase()}</span></p>
                    {a.note && <p className="mt-0.5 text-xs text-ink-2">{a.note}</p>}
                    <p className="tabular mt-0.5 text-[11px] text-ink-3">{full(a.created_at)}</p>
                  </div>
                </div>
              )) : <p className="text-sm text-ink-3">No action yet.</p>}
            </div>
          </Card>
        </div>
      </div>

      <Modal open={Boolean(pending)} onClose={() => setPending(null)}
        title={pending === 'REPORT_LOST_DEVICE' ? 'Report lost device' : ACTIONS.find(([k]) => k === pending)?.[1] || 'Reopen'}
        subtitle={pending === 'REPORT_LOST_DEVICE' ? 'Opens a breach record and starts the 72-hour Art. 33 clock.' : `INC-${incident.number}`}
        footer={<><Button variant="ghost" onClick={() => setPending(null)}>Cancel</Button><Button variant="primary" loading={busy} onClick={act}>Confirm</Button></>}>
        <Textarea autoFocus placeholder={['RESOLVE', 'FALSE_POSITIVE'].includes(pending) ? 'Required: explain the decision' : 'Note (optional)'}
          value={note} onChange={(e) => setNote(e.target.value)} />
        <ErrorNote>{error}</ErrorNote>
      </Modal>
    </>
  )
}
