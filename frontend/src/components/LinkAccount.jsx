import { useEffect, useState } from 'react'
import api, { errorText } from '../lib/api'
import { Button, ErrorNote, Field, Input, Modal, Select } from './ui'

/**
 * Link a Windows account to an employee. Either the account or the employee can be fixed by the caller.
 * Accounts already seen by agents are offered as suggestions, so a typo (MACKBOOK\…) is hard to make.
 */
export default function LinkAccountModal({ open, onClose, onLinked, account: fixedAccount, employee: fixedEmployee }) {
  const [employees, setEmployees] = useState([])
  const [seen, setSeen] = useState([])
  const [account, setAccount] = useState('')
  const [employee, setEmployee] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    setAccount(fixedAccount || '')
    setEmployee(fixedEmployee?.id || '')
    setError('')
    setResult(null)
    api.get('/admin/employees/').then((r) => setEmployees(r.data)).catch(() => {})
    api.get('/admin/unlinked-accounts/').then((r) => setSeen([...new Set(r.data.map((row) => row.account))])).catch(() => {})
  }, [open, fixedAccount, fixedEmployee])

  const valid = /^[^\\\s]+\\[^\\\s]+$/.test(account.trim())
  const unknown = valid && seen.length > 0 && !seen.some((a) => a.toLowerCase() === account.trim().toLowerCase())

  async function link() {
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post(`/admin/employees/${employee}/accounts/`, { account: account.trim() })
      setResult(data)
      onLinked?.(data)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const name = employees.find((e) => e.id === employee)?.full_name
  return (
    <Modal open={open} onClose={onClose} title="Link Windows account"
      subtitle="Activity from this account will count as this employee's, checked against their permissions and shift."
      footer={result
        ? <Button variant="primary" onClick={onClose}>Done</Button>
        : <><Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={busy} disabled={!valid || !employee} onClick={link}>Link</Button></>}>
      {result ? (
        <div className="space-y-2 text-sm">
          <p className="font-medium text-ink">{result.account} is now linked to {name}.</p>
          <p className="text-ink-2">
            {result.events_relinked
              ? `${result.events_relinked} past event(s) moved to ${name} and checked again: ${result.incidents_replaced} incident(s) replaced, ${result.incidents_raised} raised.`
              : 'No activity has been seen from this account yet. Its next events will be attributed to this employee.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <Field label="Windows account" hint={unknown ? 'Agents have not seen this account yet. Check the spelling, for example MACBOOK\\bilal.' : 'Format MACHINE\\username, as shown under "Accounts seen by agents".'}>
            {fixedAccount ? <Input value={account} disabled className="font-mono" /> : (
              <>
                <Input list="seen-accounts" className="font-mono" placeholder="MACBOOK\bilal" value={account} onChange={(e) => setAccount(e.target.value)} />
                <datalist id="seen-accounts">{seen.map((a) => <option key={a} value={a} />)}</datalist>
              </>
            )}
          </Field>
          <Field label="Employee">
            {fixedEmployee ? <Input value={fixedEmployee.full_name} disabled /> : (
              <Select value={employee} onChange={(e) => setEmployee(e.target.value)} placeholder="Choose employee…"
                options={Object.fromEntries(employees.map((e) => [e.id, `${e.full_name} (${e.employee_code})`]))} />
            )}
          </Field>
          <ErrorNote>{error}</ErrorNote>
        </div>
      )}
    </Modal>
  )
}
