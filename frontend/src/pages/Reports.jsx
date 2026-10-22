import { useState } from 'react'
import { Download, FileText } from 'lucide-react'
import { download, errorText } from '../lib/api'
import { Button, Card, CardHeader, ErrorNote, Field, PageHeader, Select } from '../components/ui'

export default function Reports() {
  const [days, setDays] = useState('7')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function get() {
    setBusy(true)
    setError('')
    try {
      const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
      await download(`/reports/compliance.pdf?days=${days}`, `auditra_compliance_${stamp}.pdf`)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Reports" subtitle="PDF compliance report generated from live data at the moment you download it." />
      <Card className="max-w-2xl">
        <CardHeader icon={FileText} title="Compliance report" subtitle="Summary, GDPR articles, employee risk, every incident with its score, and controls" />
        <div className="flex flex-wrap items-end gap-3 px-5 py-4">
          <Field label="Period" className="w-48">
            <Select value={days} onChange={(e) => setDays(e.target.value)} options={[['1', 'Last 24 hours'], ['7', 'Last 7 days'], ['30', 'Last 30 days'], ['90', 'Last 90 days']]} />
          </Field>
          <Button variant="primary" icon={Download} loading={busy} onClick={get}>Download PDF</Button>
        </div>
        <div className="px-5 pb-4"><ErrorNote>{error}</ErrorNote></div>
        <p className="border-t border-line px-5 py-3 text-xs text-ink-3">Per-employee reports are on each employee's profile.</p>
      </Card>
    </>
  )
}
