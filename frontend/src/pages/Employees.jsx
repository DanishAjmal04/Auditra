import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, Minus, Users } from 'lucide-react'
import api from '../lib/api'
import { useLive } from '../lib/live'
import { CATEGORIES, ago } from '../lib/format'
import { Card, Empty, PageHeader, Pill, ScoreBar, Spinner, Table, Tabs, cx } from '../components/ui'

const level = (score) => (score >= 85 ? 'CRITICAL' : score >= 65 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW')
const SENS = { LOW: 1, MEDIUM: 2, HIGH: 3 }

export default function Employees() {
  const { version } = useLive()
  const navigate = useNavigate()
  const [rows, setRows] = useState(null)
  const [catalogue, setCatalogue] = useState([])
  const [tab, setTab] = useState('directory')

  useEffect(() => { api.get('/employees/').then((r) => setRows(r.data)) }, [version])
  useEffect(() => { api.get('/catalogue/').then((r) => setCatalogue(r.data)) }, [])

  const columns = [
    { key: 'name', label: 'Employee', render: (r) => (
      <div><p className="font-medium">{r.full_name}</p><p className="text-xs text-ink-3">{r.employee_code} · {r.department}</p></div>
    ) },
    { key: 'role', label: 'Role & type', render: (r) => (
      <div className="flex flex-wrap gap-1">
        <Pill>{r.role}</Pill>
        {r.employment_type === 'VENDOR' && <Pill tone="warn">Vendor</Pill>}
        {r.status === 'LEFT' && <Pill tone="crit">Left</Pill>}
      </div>
    ) },
    { key: 'access', label: 'May access', render: (r) => (
      <div className="text-xs text-ink-2">
        <p>up to <span className="font-medium text-ink">{r.max_sensitivity}</span> · shift <span className="tabular">{r.shift}</span></p>
        <p className="mt-0.5 text-ink-3">{r.allowed_categories.length ? r.allowed_categories.join(', ') : 'General only'}</p>
      </div>
    ) },
    { key: 'accounts', label: 'Windows accounts', render: (r) => (
      <div className="flex flex-col gap-0.5 font-mono text-[11px] text-ink-2">{r.accounts.length ? r.accounts.map((a) => <span key={a}>{a}</span>) : <span className="text-ink-3">none linked</span>}</div>
    ) },
    { key: 'open', label: 'Open', render: (r) => (
      <div className="text-xs">
        <span className="tabular text-ink">{r.open_incidents}</span>
        {r.repeat_offender && <Pill tone="crit" className="ml-2">Art. 83</Pill>}
      </div>
    ) },
    { key: 'risk', label: 'Risk', render: (r) => <ScoreBar score={r.risk_score} severity={level(r.risk_score)} /> },
    { key: 'ai', label: 'AI today', render: (r) => (
      <span className={cx('tabular text-xs font-semibold', r.ai_score_today >= 60 ? 'text-high' : 'text-ink-3')}>
        {r.ai_score_today != null ? Math.round(r.ai_score_today) : '—'}
      </span>
    ) },
    { key: 'seen', label: 'Last activity', render: (r) => <span className="text-xs text-ink-3">{ago(r.last_activity)}</span> },
  ]

  return (
    <>
      <PageHeader title="Employees" subtitle="Who works here, what each person may access, and how risky their activity is right now." />
      <Tabs value={tab} onChange={setTab} tabs={[['directory', 'Directory', rows?.length], ['matrix', 'Access matrix']]} />
      {rows === null ? <Spinner /> : !rows.length ? (
        <Card><Empty icon={Users} title="No employees yet">An administrator adds employees and links their Windows accounts under Employees &amp; Access.</Empty></Card>
      ) : tab === 'directory' ? (
        <Card><Table columns={columns} rows={rows} onRowClick={(r) => navigate(`/employees/${r.id}`)} /></Card>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-[11px] uppercase tracking-wider text-ink-3">
                <th className="px-4 py-2.5 text-left font-medium">Data in the catalogue</th>
                {rows.map((r) => <th key={r.id} className="px-3 py-2.5 text-center font-medium normal-case tracking-normal">{r.full_name}<br /><span className="text-ink-3">{r.role}</span></th>)}
              </tr>
            </thead>
            <tbody>
              {catalogue.map((entry) => (
                <tr key={entry.id} className="border-b border-line/70">
                  <td className="px-4 py-2.5">
                    <p className="font-medium">{entry.name}</p>
                    <p className="text-xs text-ink-3">{CATEGORIES[entry.category]} · {entry.sensitivity}</p>
                  </td>
                  {rows.map((r) => {
                    const ok = (entry.category === 'GENERAL' || r.allowed_categories.includes(entry.category))
                      && SENS[entry.sensitivity] <= SENS[r.max_sensitivity] && r.status === 'ACTIVE'
                    return (
                      <td key={r.id} className="px-3 py-2.5 text-center">
                        {ok ? <Check size={16} className="mx-auto text-ok" /> : <Minus size={16} className="mx-auto text-ink-3" />}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          {!catalogue.length && <Empty title="The data catalogue is empty" />}
        </Card>
      )}
    </>
  )
}
