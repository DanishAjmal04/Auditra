import { useEffect, useState } from 'react'
import { Link2, UserCog, UserRoundSearch, X } from 'lucide-react'
import api, { errorText } from '../../lib/api'
import { useLive } from '../../lib/live'
import { CATEGORIES, DAYS, EMPLOYEE_ROLES, ago } from '../../lib/format'
import Crud from '../../components/Crud'
import { Button, Card, CardHeader, Empty, ErrorNote, Modal, PageHeader, Pill, Select } from '../../components/ui'

const DAY_OPTIONS = Object.fromEntries(DAYS.map((d, i) => [i, d]))

function AccountsCell({ row, reload }) {
  async function unlink(account) {
    if (!window.confirm(`Unlink ${account.account} from ${row.full_name}?`)) return
    await api.delete(`/admin/employees/${row.id}/accounts/${account.id}/`)
    reload()
  }
  return (
    <div className="flex flex-col gap-1">
      {row.accounts.map((a) => (
        <span key={a.id} className="inline-flex items-center gap-1 font-mono text-[11px] text-ink-2">
          {a.account}
          <button onClick={(e) => { e.stopPropagation(); unlink(a) }} className="text-ink-3 hover:text-crit"><X size={11} /></button>
        </span>
      ))}
      {!row.accounts.length && <span className="text-xs text-ink-3">none</span>}
    </div>
  )
}

function Unlinked({ employees, onLinked, version }) {
  const [rows, setRows] = useState([])
  const [linking, setLinking] = useState(null)
  const [employee, setEmployee] = useState('')
  const [error, setError] = useState('')
  useEffect(() => { api.get('/admin/unlinked-accounts/').then((r) => setRows(r.data)) }, [version])

  async function link() {
    setError('')
    try {
      await api.post(`/admin/employees/${employee}/accounts/`, { account: linking.account })
      setLinking(null)
      onLinked()
      api.get('/admin/unlinked-accounts/').then((r) => setRows(r.data))
    } catch (e) { setError(errorText(e)) }
  }

  return (
    <Card>
      <CardHeader icon={UserRoundSearch} title="Accounts seen by agents but not linked" subtitle="Link each Windows account to the employee who uses it. Past events follow the link." />
      {rows.length ? (
        <div className="divide-y divide-line/70">
          {rows.map((r) => (
            <div key={`${r.account}-${r.machine}`} className="flex items-center gap-4 px-4 py-2.5 text-sm">
              <span className="flex-1 font-mono text-xs">{r.account}</span>
              <span className="text-xs text-ink-3">{r.machine}</span>
              <span className="tabular text-xs text-ink-3">{r.events} events · {ago(r.last_seen)}</span>
              <Button size="sm" icon={Link2} onClick={() => { setLinking(r); setEmployee(''); setError('') }}>Link</Button>
            </div>
          ))}
        </div>
      ) : <Empty title="Every account seen so far is linked" />}
      <Modal open={Boolean(linking)} onClose={() => setLinking(null)} title="Link Windows account" subtitle={linking?.account}
        footer={<><Button variant="ghost" onClick={() => setLinking(null)}>Cancel</Button><Button variant="primary" disabled={!employee} onClick={link}>Link</Button></>}>
        <Select value={employee} onChange={(e) => setEmployee(e.target.value)} placeholder="Choose employee…"
          options={Object.fromEntries(employees.map((e) => [e.id, `${e.full_name} (${e.employee_code})`]))} />
        <div className="mt-3"><ErrorNote>{error}</ErrorNote></div>
      </Modal>
    </Card>
  )
}

export default function AdminEmployees() {
  const { version } = useLive()
  const [employees, setEmployees] = useState([])
  const [tick, setTick] = useState(0)
  const [adding, setAdding] = useState(null)
  const [account, setAccount] = useState('')
  const [error, setError] = useState('')

  useEffect(() => { api.get('/admin/employees/').then((r) => setEmployees(r.data)) }, [tick])

  async function addAccount() {
    setError('')
    try {
      await api.post(`/admin/employees/${adding.id}/accounts/`, { account })
      setAdding(null)
      setTick((t) => t + 1)
    } catch (e) { setError(errorText(e)) }
  }

  return (
    <>
      <PageHeader title="Employees & access" subtitle="Who may see what, and when. These permissions are what the role-scope, category, shift and vendor rules check." />
      <div className="space-y-4">
        <Crud title="Employee" icon={UserCog} path="/admin/employees/" deps={[tick]} onSaved={() => setTick((t) => t + 1)}
          defaults={{ role: 'STAFF', employment_type: 'STAFF', status: 'ACTIVE', shift_start: '09:00', shift_end: '18:00', work_days: [0, 1, 2, 3, 4], max_sensitivity: 'MEDIUM', allowed_categories: [] }}
          fields={[
            { name: 'full_name', label: 'Full name', half: true },
            { name: 'employee_code', label: 'Employee code', half: true, placeholder: 'E-1001' },
            { name: 'department', label: 'Department', half: true, placeholder: 'Finance' },
            { name: 'email', label: 'Email', type: 'email', half: true },
            { name: 'role', label: 'Role', type: 'select', options: EMPLOYEE_ROLES, half: true },
            { name: 'employment_type', label: 'Type', type: 'select', options: { STAFF: 'Staff', VENDOR: 'Vendor / processor (Art. 29)' }, half: true },
            { name: 'shift_start', label: 'Shift starts', type: 'time', half: true },
            { name: 'shift_end', label: 'Shift ends', type: 'time', half: true },
            { name: 'work_days', label: 'Working days', type: 'multiselect', options: DAY_OPTIONS },
            { name: 'max_sensitivity', label: 'Highest sensitivity allowed', type: 'select', options: ['LOW', 'MEDIUM', 'HIGH'], half: true },
            { name: 'status', label: 'Status', type: 'select', options: { ACTIVE: 'Active', LEFT: 'Left the organisation' }, half: true },
            { name: 'allowed_categories', label: 'Data categories allowed', type: 'multiselect', options: CATEGORIES, hint: 'General business data is always allowed' },
          ]}
          columns={[
            { key: 'n', label: 'Employee', render: (r) => <div><p className="font-medium">{r.full_name}</p><p className="text-xs text-ink-3">{r.employee_code} · {r.department} · {r.role_label}</p></div> },
            { key: 't', label: 'Status', render: (r) => <div className="flex flex-wrap gap-1">{r.employment_type === 'VENDOR' && <Pill tone="warn">Vendor</Pill>}<Pill tone={r.status === 'ACTIVE' ? 'ok' : 'crit'}>{r.status.toLowerCase()}</Pill></div> },
            { key: 's', label: 'Shift', render: (r) => <span className="tabular text-xs text-ink-2">{r.shift_start.slice(0, 5)}–{r.shift_end.slice(0, 5)}<br />{r.work_days.map((d) => DAYS[d]).join(' ')}</span> },
            { key: 'p', label: 'Permissions', render: (r) => <div className="text-xs text-ink-2">up to {r.max_sensitivity}<div className="mt-1 flex flex-wrap gap-1">{r.allowed_categories.map((c) => <Pill key={c}>{c}</Pill>)}</div></div> },
            { key: 'a', label: 'Windows accounts', render: (r) => <AccountsCell row={r} reload={() => setTick((t) => t + 1)} /> },
          ]}
          extraActions={(row) => <Button size="sm" variant="ghost" icon={Link2} title="Link account" onClick={() => { setAdding(row); setAccount(''); setError('') }} />}
          emptyText="No employees yet. Add the people whose laptops are monitored."
        />
        <Unlinked employees={employees} version={version} onLinked={() => setTick((t) => t + 1)} />
      </div>
      <Modal open={Boolean(adding)} onClose={() => setAdding(null)} title="Link Windows account" subtitle={adding?.full_name}
        footer={<><Button variant="ghost" onClick={() => setAdding(null)}>Cancel</Button><Button variant="primary" onClick={addAccount}>Link</Button></>}>
        <input className="h-9 w-full rounded-lg border border-line-2 bg-canvas px-3 font-mono text-sm outline-none focus:border-accent" autoFocus
          placeholder="MACBOOK\bilal" value={account} onChange={(e) => setAccount(e.target.value)} />
        <p className="mt-2 text-xs text-ink-3">Format MACHINE\username. Microsoft accounts appear as MICROSOFTACCOUNT\email.</p>
        <div className="mt-3"><ErrorNote>{error}</ErrorNote></div>
      </Modal>
    </>
  )
}
