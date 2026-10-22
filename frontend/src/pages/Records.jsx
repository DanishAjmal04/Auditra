import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { BadgeCheck, Bot, FileWarning, HandHeart, Inbox, ListChecks, UserRound } from 'lucide-react'
import api, { errorText } from '../lib/api'
import { useLive } from '../lib/live'
import { LAWFUL_BASES, full } from '../lib/format'
import Crud, { RecordForm, useCollection } from '../components/Crud'
import { Button, Card, CardHeader, ErrorNote, PageHeader, Pill, Tabs } from '../components/ui'

const RIGHTS = {
  ACCESS: 'Access (Art. 15)', RECTIFICATION: 'Rectification (Art. 16)', ERASURE: 'Erasure (Art. 17)',
  RESTRICTION: 'Restriction (Art. 18)', PORTABILITY: 'Portability (Art. 20)', OBJECTION: 'Objection (Art. 21)',
}
const REQUEST_STATUS = { PENDING: 'Pending', IN_PROGRESS: 'In progress', COMPLETED: 'Completed', DENIED: 'Denied' }

function useSubjects(deps) {
  const [subjects] = useCollection('/records/subjects/', deps)
  return Object.fromEntries((subjects || []).map((s) => [s.id, `${s.name} (${s.reference})`]))
}

function Subjects() {
  return (
    <Crud title="Data subject" icon={UserRound} path="/records/subjects/"
      subtitle="People whose data the organisation holds. The file path links them to activity on monitored machines."
      fields={[
        { name: 'name', label: 'Name', half: true },
        { name: 'reference', label: 'Reference', half: true, placeholder: 'C-501' },
        { name: 'email', label: 'Email', type: 'email' },
        { name: 'path_prefix', label: 'File or folder holding their data', placeholder: 'C:\\AuditraCompany\\Customers\\ali_khan_profile.csv' },
      ]}
      columns={[
        { key: 'name', label: 'Subject', render: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-ink-3">{r.reference}</p></div> },
        { key: 'path', label: 'Data location', render: (r) => <span className="break-all font-mono text-[11px] text-ink-2">{r.path_prefix || '—'}</span> },
        { key: 'consent', label: 'Consent', render: (r) => <Pill tone={r.consent_status === 'GIVEN' ? 'ok' : r.consent_status === 'WITHDRAWN' ? 'crit' : 'default'}>{r.consent_status.toLowerCase()}</Pill> },
        { key: 'req', label: 'Open requests', render: (r) => <span className="tabular text-ink-2">{r.open_requests}</span> },
      ]}
    />
  )
}

function Consents({ version }) {
  const subjects = useSubjects([version])
  return (
    <Crud title="Consent record" icon={HandHeart} path="/records/consents/" deps={[version]}
      subtitle="Art. 7: when consent is withdrawn, any later access to that person's data is flagged."
      defaults={{ lawful_basis: 'CONSENT', status: 'GIVEN', given_at: new Date().toISOString() }}
      fields={[
        { name: 'data_subject', label: 'Data subject', type: 'select', options: subjects, placeholder: 'Choose…' },
        { name: 'purpose', label: 'Purpose', placeholder: 'Marketing emails' },
        { name: 'lawful_basis', label: 'Lawful basis', type: 'select', options: LAWFUL_BASES, half: true },
        { name: 'status', label: 'Status', type: 'select', options: { GIVEN: 'Given', WITHDRAWN: 'Withdrawn' }, half: true },
        { name: 'given_at', label: 'Given at', type: 'datetime', half: true },
        { name: 'withdrawn_at', label: 'Withdrawn at', type: 'datetime', half: true, hint: 'Filled automatically when status is Withdrawn' },
      ]}
      columns={[
        { key: 's', label: 'Subject', render: (r) => r.data_subject_name },
        { key: 'p', label: 'Purpose', render: (r) => <span className="text-ink-2">{r.purpose}</span> },
        { key: 'b', label: 'Basis', render: (r) => LAWFUL_BASES[r.lawful_basis] },
        { key: 'st', label: 'Status', render: (r) => <Pill tone={r.status === 'GIVEN' ? 'ok' : 'crit'}>{r.status.toLowerCase()}</Pill> },
        { key: 'w', label: 'Withdrawn', render: (r) => <span className="tabular text-xs text-ink-3">{r.withdrawn_at ? full(r.withdrawn_at) : '—'}</span> },
      ]}
    />
  )
}

function Requests({ version }) {
  const subjects = useSubjects([version])
  return (
    <Crud title="Data-subject request" icon={Inbox} path="/records/requests/" deps={[version]}
      subtitle="Art. 15–21. Deadline is 30 days from receipt. Overdue requests become incidents automatically."
      defaults={{ right_type: 'ACCESS', status: 'PENDING', received_at: new Date().toISOString() }}
      fields={[
        { name: 'data_subject', label: 'Data subject', type: 'select', options: subjects, placeholder: 'Choose…' },
        { name: 'right_type', label: 'Right', type: 'select', options: RIGHTS, half: true },
        { name: 'status', label: 'Status', type: 'select', options: REQUEST_STATUS, half: true },
        { name: 'received_at', label: 'Received', type: 'datetime', half: true },
        { name: 'response_deadline', label: 'Deadline', type: 'datetime', half: true, hint: 'Leave empty for received + 30 days' },
        { name: 'exemption_note', label: 'Exemption (required to deny portability)', type: 'textarea' },
        { name: 'notes', label: 'Notes', type: 'textarea' },
      ]}
      columns={[
        { key: 's', label: 'Subject', render: (r) => r.data_subject_name },
        { key: 'r', label: 'Right', render: (r) => <Pill tone="accent">Art. {r.article}</Pill> },
        { key: 'st', label: 'Status', render: (r) => <span className="text-ink-2">{REQUEST_STATUS[r.status]}</span> },
        { key: 'd', label: 'Deadline', render: (r) => <span className={`tabular text-xs ${r.overdue ? 'font-semibold text-crit' : 'text-ink-2'}`}>{full(r.response_deadline)}{r.overdue && ' · overdue'}</span> },
      ]}
    />
  )
}

function Breaches({ version }) {
  return (
    <Crud title="Breach record" icon={FileWarning} path="/records/breaches/" deps={[version]}
      subtitle="Art. 33: notify the authority within 72 hours. Art. 34: notify subjects of a high-risk breach."
      defaults={{ severity: 'HIGH', high_risk: true, detected_at: new Date().toISOString() }}
      fields={[
        { name: 'title', label: 'Title' },
        { name: 'description', label: 'Description', type: 'textarea' },
        { name: 'severity', label: 'Severity', type: 'select', options: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], half: true },
        { name: 'detected_at', label: 'Detected', type: 'datetime', half: true },
        { name: 'high_risk', label: 'High risk to data subjects (Art. 34 applies)', type: 'checkbox' },
        { name: 'authority_notified_at', label: 'Authority notified', type: 'datetime', half: true },
        { name: 'subjects_notified_at', label: 'Subjects notified', type: 'datetime', half: true },
      ]}
      columns={[
        { key: 't', label: 'Breach', render: (r) => <div><p className="font-medium">{r.title}</p>{r.incident_number && <Link to={`/incidents/${r.incident}`} className="text-xs text-accent hover:underline">from INC-{r.incident_number}</Link>}</div> },
        { key: 'sev', label: 'Severity', render: (r) => <Pill tone={['HIGH', 'CRITICAL'].includes(r.severity) ? 'crit' : 'default'}>{r.severity}</Pill> },
        { key: 'clock', label: '72-hour clock', render: (r) => r.authority_notified_at
          ? <Pill tone="ok">authority notified</Pill>
          : <span className={`tabular text-xs font-semibold ${r.hours_left < 0 ? 'text-crit' : r.hours_left < 24 ? 'text-high' : 'text-ink-2'}`}>{r.hours_left < 0 ? `${Math.abs(r.hours_left)} h overdue` : `${r.hours_left} h left`}</span> },
        { key: 'sub', label: 'Subjects', render: (r) => r.high_risk ? (r.subjects_notified_at ? <Pill tone="ok">notified</Pill> : <Pill tone="warn">not notified</Pill>) : <span className="text-xs text-ink-3">not required</span> },
      ]}
    />
  )
}

function Processing() {
  return (
    <Crud title="Processing activity" icon={ListChecks} path="/records/processing/"
      subtitle="Records of Processing Activities (Art. 30). A catalogue folder without one is flagged; one without a lawful basis is Art. 6."
      fields={[
        { name: 'activity_name', label: 'Activity' },
        { name: 'purpose', label: 'Purpose' },
        { name: 'legal_basis', label: 'Lawful basis', type: 'select', options: LAWFUL_BASES, placeholder: '— none recorded —' },
        { name: 'data_categories', label: 'Data categories', type: 'textarea' },
        { name: 'retention_period', label: 'Retention period', half: true },
        { name: 'security_measures', label: 'Security measures', type: 'textarea' },
      ]}
      columns={[
        { key: 'a', label: 'Activity', render: (r) => <div><p className="font-medium">{r.activity_name}</p><p className="text-xs text-ink-3">{r.purpose}</p></div> },
        { key: 'b', label: 'Lawful basis', render: (r) => r.legal_basis ? LAWFUL_BASES[r.legal_basis] : <Pill tone="crit">missing (Art. 6)</Pill> },
        { key: 'r', label: 'Retention', render: (r) => <span className="text-ink-2">{r.retention_period || '—'}</span> },
      ]}
    />
  )
}

function Decisions({ version }) {
  return (
    <Crud title="Automated decision" icon={Bot} path="/records/decisions/" deps={[version]} canCreate={false} canDelete={false}
      subtitle="Sent by business systems to POST /api/decisions/. A significant decision with no human review within 1 hour is Art. 22."
      fields={[{ name: 'reviewed_by', label: 'Reviewed by' }, { name: 'reviewed_at', label: 'Reviewed at', type: 'datetime' }]}
      extraActions={(row, reload) => !row.reviewed_at && (
        <Button size="sm" icon={BadgeCheck} onClick={() => api.post(`/records/decisions/${row.id}/review/`).then(reload)}>Review</Button>
      )}
      emptyText="No automated decisions received from business systems"
      columns={[
        { key: 's', label: 'System', render: (r) => <span className="font-medium">{r.system}</span> },
        { key: 'd', label: 'Decision', render: (r) => <div><p>{r.decision}</p><p className="text-xs text-ink-3">subject {r.subject_reference}</p></div> },
        { key: 'm', label: 'Made', render: (r) => <span className="tabular text-xs text-ink-2">{full(r.made_at)}</span> },
        { key: 'rv', label: 'Human review', render: (r) => r.reviewed_at ? <Pill tone="ok">{r.reviewed_by}</Pill> : <Pill tone="warn">pending</Pill> },
      ]}
    />
  )
}

const DPO_FIELDS = [
  { name: 'organization_name', label: 'Organisation' },
  { name: 'dpo_required', label: 'A DPO is required (large-scale or special-category processing)', type: 'checkbox' },
  { name: 'name', label: 'DPO name', half: true },
  { name: 'contact', label: 'Contact email', type: 'email', half: true },
  { name: 'designated_at', label: 'Designated on', type: 'date', half: true, nullable: true },
  { name: 'scope', label: 'Scope of responsibility', type: 'textarea' },
  { name: 'independent', label: 'Acts independently (Art. 38(3))', type: 'checkbox' },
  { name: 'direct_access_to_management', label: 'Reports to highest management', type: 'checkbox' },
  { name: 'conflict_free', label: 'No conflict of interest (Art. 38(6))', type: 'checkbox' },
  { name: 'published_contact_details', label: 'Contact details published (Art. 37(7))', type: 'checkbox' },
]

function Dpo() {
  const [values, setValues] = useState(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.get('/records/dpo/').then((r) => { setValues({ ...r.data, designated_at: r.data.designated_at || '' }); setStatus(r.data.compliance_status) }) }, [])
  if (!values) return null
  async function save() {
    setBusy(true)
    setError('')
    try {
      const { data } = await api.put('/records/dpo/', { ...values, designated_at: values.designated_at || null })
      setStatus(data.compliance_status)
    } catch (e) { setError(errorText(e)) } finally { setBusy(false) }
  }
  const tone = status === 'COMPLIANT' || status === 'NOT_REQUIRED' ? 'ok' : 'crit'
  return (
    <Card>
      <CardHeader icon={BadgeCheck} title="Data Protection Officer (Art. 37)" subtitle="High-risk processing while this is incomplete raises an Art. 37 incident"
        actions={<Pill tone={tone}>{status.replace('_', ' ').toLowerCase()}</Pill>} />
      <div className="max-w-2xl px-5 py-4">
        <RecordForm fields={DPO_FIELDS} values={values} onChange={setValues} />
        <div className="mt-4 flex items-center gap-3"><Button variant="primary" loading={busy} onClick={save}>Save</Button><ErrorNote>{error}</ErrorNote></div>
      </div>
    </Card>
  )
}

export default function Records() {
  const { version } = useLive()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'subjects'
  const setTab = (value) => setParams({ tab: value })
  const views = {
    subjects: <Subjects />, consents: <Consents version={version} />, requests: <Requests version={version} />,
    breaches: <Breaches version={version} />, processing: <Processing />, decisions: <Decisions version={version} />, dpo: <Dpo />,
  }
  return (
    <>
      <PageHeader title="GDPR records" subtitle="The organisation's own compliance records. Rules combine them with live endpoint activity." />
      <Tabs value={tab} onChange={setTab} tabs={[
        ['subjects', 'Data subjects'], ['consents', 'Consent'], ['requests', 'Subject requests'], ['breaches', 'Breaches'],
        ['processing', 'Processing (RoPA)'], ['decisions', 'Automated decisions'], ['dpo', 'DPO'],
      ]} />
      {views[tab]}
    </>
  )
}
