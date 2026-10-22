import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Activity as ActivityIcon, Moon, Search, X } from 'lucide-react'
import api, { list } from '../lib/api'
import { useLive } from '../lib/live'
import { CATEGORIES, full } from '../lib/format'
import EventIcon, { eventSentence } from '../components/EventIcon'
import { Card, Checkbox, Empty, Input, PageHeader, Pill, Select, Spinner, Table } from '../components/ui'

const TYPES = {
  'LOGON,UNLOCK,LOCK': 'Logons & unlocks',
  LOGON_FAILED: 'Failed logons',
  'FILE_READ,FILE_WRITE': 'File access',
  FILE_DELETE: 'File deletions',
  'USB_CONNECTED,FILE_COPY_TO_USB': 'USB',
  PRINT: 'Printing',
  WEB_VISIT: 'Web (watched sites)',
  'ACCOUNT_CREATED,GROUP_MEMBER_ADDED,ACCOUNT_LOCKED,LOG_CLEARED,AUDIT_POLICY_CHANGED,TASK_CREATED': 'System & accounts',
  'RETENTION_EXCEEDED,AUTOMATED_DECISION': 'Retention & decisions',
}

export default function ActivityPage() {
  const { version } = useLive()
  const [params, setParams] = useSearchParams()
  const [filters, setFilters] = useState(() => ({
    type: params.get('type') || '', category: params.get('category') || '', q: params.get('q') || '',
    outside_shift: params.get('outside_shift') === '1', employee: params.get('employee') || '',
  }))
  const [rows, setRows] = useState(null)
  const [count, setCount] = useState(0)

  useEffect(() => {
    const params = { page_size: 200 }
    if (filters.type) params.type = filters.type
    if (filters.category) params.category = filters.category
    if (filters.q) params.q = filters.q
    if (filters.outside_shift) params.outside_shift = 1
    if (filters.employee) params.employee = filters.employee
    const timer = setTimeout(() => api.get('/events/', { params }).then((r) => { setRows(list(r.data)); setCount(r.data.count) }), filters.q ? 300 : 0)
    return () => clearTimeout(timer)
  }, [filters, version])

  const columns = [
    { key: 'time', label: 'When', className: 'whitespace-nowrap', render: (r) => <span className="tabular text-xs text-ink-2">{full(r.occurred_at)}</span> },
    { key: 'who', label: 'Who', render: (r) => (
      <div><p className="text-sm">{r.employee ? <Link to={`/employees/${r.employee.id}`} className="hover:text-accent">{r.employee.full_name}</Link> : <span className="text-ink-3">not linked</span>}</p><p className="font-mono text-[11px] text-ink-3">{r.account}</p></div>
    ) },
    { key: 'what', label: 'What happened', render: (r) => (
      <div className="flex items-start gap-2">
        <EventIcon type={r.event_type} className="mt-0.5 shrink-0 text-ink-3" />
        <div className="min-w-0">
          <p className="text-sm text-ink">{eventSentence(r)}</p>
          {r.path && <p className="break-all font-mono text-[11px] text-ink-3">{r.details?.source_path || r.path}</p>}
        </div>
      </div>
    ) },
    { key: 'data', label: 'Data', render: (r) => (
      <div className="flex flex-wrap gap-1">
        {r.category ? <Pill tone={r.sensitivity === 'HIGH' ? 'crit' : 'default'}>{r.category} · {r.sensitivity}</Pill> : <span className="text-xs text-ink-3">—</span>}
        {r.data_subject_name && <Pill tone="warn">{r.data_subject_name}</Pill>}
        {r.outside_shift && <Pill tone="warn"><Moon size={10} />outside shift</Pill>}
      </div>
    ) },
    { key: 'source', label: 'Source', render: (r) => <span className="text-[11px] text-ink-3">{r.machine}<br />{r.source}{r.source_event_id ? ` · ${r.source_event_id}` : ''}</span> },
  ]

  return (
    <>
      <PageHeader title="Activity log" subtitle="Clean, structured events from monitored machines. Raw Windows noise is filtered on the endpoint and never stored." />
      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
          <div className="relative min-w-60 flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
            <Input placeholder="Search file, account, site or device" className="pl-8" value={filters.q} onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))} />
          </div>
          <Select className="w-48" value={filters.type} placeholder="All activity" options={TYPES} onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value }))} />
          <Select className="w-52" value={filters.category} placeholder="Any data category" options={CATEGORIES} onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))} />
          <Checkbox label="Outside shift" checked={filters.outside_shift} onChange={(e) => setFilters((f) => ({ ...f, outside_shift: e.target.checked }))} />
          {filters.employee && (
            <button className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-1 text-xs font-medium text-accent"
              onClick={() => { setFilters((f) => ({ ...f, employee: '' })); setParams({}) }}>
              {rows?.[0]?.employee?.full_name || 'One employee'} <X size={12} />
            </button>
          )}
          <span className="tabular ml-auto text-xs text-ink-3">{count ?? 0} event(s)</span>
        </div>
        {rows === null ? <Spinner /> : <Table columns={columns} rows={rows} empty={<Empty icon={ActivityIcon} title="No events match" />} />}
      </Card>
    </>
  )
}
