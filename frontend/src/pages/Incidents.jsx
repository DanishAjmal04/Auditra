import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { Search, ShieldAlert } from 'lucide-react'
import api, { list } from '../lib/api'
import { useLive } from '../lib/live'
import { STATUS_LABEL, dayTime, who } from '../lib/format'
import { Articles, Card, Empty, Input, PageHeader, Pill, ScoreBar, Select, SeverityBadge, Spinner, Table } from '../components/ui'

export default function Incidents() {
  const { version } = useLive()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [filters, setFilters] = useState(() => ({
    status: params.get('status') ?? 'open', severity: params.get('severity') || '', kind: params.get('kind') || '',
    q: params.get('q') || '', employee: params.get('employee') || '', rule: params.get('rule') || '',
  }))
  const [rows, setRows] = useState(null)
  const [count, setCount] = useState(0)

  useEffect(() => {
    const params = { page_size: 200 }
    Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v })
    const timer = setTimeout(() => {
      api.get('/incidents/', { params }).then((r) => { setRows(list(r.data)); setCount(r.data.count ?? list(r.data).length) })
    }, filters.q ? 300 : 0)
    return () => clearTimeout(timer)
  }, [filters, version])

  const set = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }))

  const columns = [
    { key: 'sev', label: 'Risk', className: 'w-28', render: (r) => <SeverityBadge severity={r.severity} /> },
    { key: 'title', label: 'Potential violation', render: (r) => (
      <div className="min-w-0">
        <p className="font-medium text-ink">{r.title}</p>
        <p className="mt-0.5 line-clamp-1 max-w-xl text-xs text-ink-3">{r.summary}</p>
      </div>
    ) },
    { key: 'who', label: 'Who', render: (r) => <span className="text-ink-2">{who(r)}</span> },
    { key: 'articles', label: 'GDPR', render: (r) => <Articles items={r.articles} max={3} /> },
    { key: 'score', label: 'Score', render: (r) => <ScoreBar score={r.score} severity={r.severity} /> },
    { key: 'status', label: 'Status', render: (r) => (
      <div className="flex flex-col gap-1">
        <span className="text-xs text-ink-2">{STATUS_LABEL[r.status]}</span>
        {r.kind !== 'VIOLATION' && <Pill tone={r.kind === 'ANOMALY' ? 'accent' : 'default'}>{r.kind === 'ANOMALY' ? 'AI anomaly' : 'Indicator'}</Pill>}
      </div>
    ) },
    { key: 'when', label: 'Detected', className: 'whitespace-nowrap', render: (r) => (
      <div className="text-xs"><p className="tabular text-ink-2">{dayTime(r.detected_at)}</p><p className="text-ink-3">INC-{r.number}</p></div>
    ) },
  ]

  return (
    <>
      <PageHeader title="Incidents" subtitle="Every potential violation, risk indicator and AI anomaly, with its evidence and the officer's decision." />
      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
          <div className="relative min-w-60 flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
            <Input placeholder="Search title, summary, employee or account" className="pl-8" value={filters.q} onChange={set('q')} />
          </div>
          <Select className="w-44" value={filters.status} onChange={set('status')}
            options={[['open', 'Open (not closed)'], ['', 'Any status'], ...Object.entries(STATUS_LABEL)]} />
          <Select className="w-36" value={filters.severity} onChange={set('severity')} placeholder="Any risk"
            options={['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']} />
          <Select className="w-44" value={filters.kind} onChange={set('kind')} placeholder="All kinds"
            options={[['VIOLATION', 'Potential violations'], ['ANOMALY', 'AI anomalies'], ['INDICATOR', 'Risk indicators']]} />
          {(filters.employee || filters.rule) && (
            <button className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-1 text-xs font-medium text-accent"
              onClick={() => { setFilters((f) => ({ ...f, employee: '', rule: '' })); setParams({}) }}>
              {filters.employee ? (rows?.[0]?.employee?.full_name || 'One employee') : `Rule ${filters.rule}`} <X size={12} />
            </button>
          )}
          <span className="tabular ml-auto text-xs text-ink-3">{count} incident(s)</span>
        </div>
        {rows === null ? <Spinner /> : (
          <Table columns={columns} rows={rows} onRowClick={(r) => navigate(`/incidents/${r.id}`)}
            empty={<Empty icon={ShieldAlert} title="Nothing matches these filters" />} />
        )}
      </Card>
    </>
  )
}
