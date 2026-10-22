import { useEffect, useState } from 'react'
import api from '../../lib/api'
import { Articles, Card, PageHeader, Pill, SeverityBadge, Spinner, Tabs, cx } from '../../components/ui'

const SOURCES = { EVENT: 'Endpoint events', WINDOW: 'Patterns over time', WORKFLOW: 'GDPR records', AI: 'AI model' }

export default function Rules() {
  const [rules, setRules] = useState(null)
  const [tab, setTab] = useState('EVENT')
  useEffect(() => { api.get('/rules/').then((r) => setRules(r.data)) }, [])

  async function toggle(rule) {
    const { data } = await api.patch(`/rules/${rule.id}/`, { enabled: !rule.enabled })
    setRules((all) => all.map((r) => (r.id === data.id ? { ...r, ...data } : r)))
  }

  if (!rules) return <Spinner />
  const shown = rules.filter((r) => r.source === tab)
  return (
    <>
      <PageHeader title="Detection rules" subtitle={`${rules.filter((r) => r.enabled).length} of ${rules.length} enabled. One rule per row of the team's GDPR violation mapping workbook.`} />
      <Tabs value={tab} onChange={setTab} tabs={Object.entries(SOURCES).map(([k, v]) => [k, v, rules.filter((r) => r.source === k).length])} />
      <Card className="divide-y divide-line/70">
        {shown.map((rule) => (
          <div key={rule.id} className={cx('flex items-start gap-4 px-4 py-3', !rule.enabled && 'opacity-50')}>
            <button onClick={() => toggle(rule)} className={cx('mt-0.5 h-5 w-9 shrink-0 rounded-full p-0.5 transition-colors', rule.enabled ? 'bg-accent' : 'bg-line-2')}>
              <span className={cx('block h-4 w-4 rounded-full bg-white transition-transform', rule.enabled && 'translate-x-4')} />
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium">{rule.title}</p>
                <SeverityBadge severity={rule.severity} />
                {rule.kind !== 'VIOLATION' && <Pill>{rule.kind === 'INDICATOR' ? 'risk indicator' : 'AI anomaly'}</Pill>}
                <Articles items={rule.articles} max={6} />
              </div>
              <p className="mt-1 text-sm text-ink-2">{rule.description}</p>
              <p className="mt-1 font-mono text-[11px] text-ink-3">{rule.code} · {rule.incident_count} incident(s)</p>
            </div>
          </div>
        ))}
      </Card>
    </>
  )
}
