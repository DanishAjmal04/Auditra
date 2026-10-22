import { Link } from 'react-router-dom'
import { FolderLock } from 'lucide-react'
import { useCollection } from '../../components/Crud'
import Crud from '../../components/Crud'
import { CATEGORIES } from '../../lib/format'
import { PageHeader, Pill } from '../../components/ui'

export default function Catalogue() {
  const [activities] = useCollection('/records/processing/')
  const activityOptions = Object.fromEntries((activities || []).map((a) => [a.id, `${a.activity_name}${a.legal_basis ? '' : ' (no lawful basis)'}`]))
  return (
    <>
      <PageHeader title="Data catalogue" subtitle="Maps folders and files on monitored machines to the personal data they hold. Agents receive these paths and audit only them." />
      <Crud title="Catalogue entry" icon={FolderLock} path="/catalogue/"
        defaults={{ category: 'GENERAL', sensitivity: 'MEDIUM' }}
        fields={[
          { name: 'name', label: 'Name', placeholder: 'Payroll' },
          { name: 'path_prefix', label: 'Folder or file path', placeholder: 'C:\\AuditraCompany\\Payroll', hint: 'The most specific path wins, so a single file can override its folder' },
          { name: 'category', label: 'Data category', type: 'select', options: CATEGORIES, half: true },
          { name: 'sensitivity', label: 'Sensitivity', type: 'select', options: ['LOW', 'MEDIUM', 'HIGH'], half: true },
          { name: 'processing_activity', label: 'Processing activity (RoPA)', type: 'select', options: activityOptions, nullable: true, placeholder: '— not in RoPA (Art. 30) —' },
          { name: 'owner_department', label: 'Owning department', half: true },
          { name: 'retention_days', label: 'Retention (days)', type: 'number', half: true, hint: 'Older files are flagged under Art. 5(1)(e)' },
        ]}
        columns={[
          { key: 'n', label: 'Entry', render: (r) => <div><Link to={`/activity?q=${encodeURIComponent(r.path_prefix.split('\\').pop())}`} className="font-medium hover:text-accent">{r.name}</Link><p className="break-all font-mono text-[11px] text-ink-3">{r.path_prefix}</p></div> },
          { key: 'c', label: 'Category', render: (r) => <span className="text-ink-2">{CATEGORIES[r.category]}</span> },
          { key: 's', label: 'Sensitivity', render: (r) => <Pill tone={r.sensitivity === 'HIGH' ? 'crit' : r.sensitivity === 'MEDIUM' ? 'warn' : 'default'}>{r.sensitivity}</Pill> },
          { key: 'p', label: 'RoPA', render: (r) => r.processing_activity_name ? <span className="text-ink-2">{r.processing_activity_name}</span> : <Pill tone="crit">missing</Pill> },
          { key: 'r', label: 'Retention', render: (r) => <span className="tabular text-xs text-ink-2">{r.retention_days ? `${r.retention_days} days` : '—'}</span> },
        ]}
        emptyText="Add the folders that hold personal data, e.g. C:\AuditraCompany\Payroll"
      />
    </>
  )
}
