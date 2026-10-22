import { useEffect, useState } from 'react'
import { ScrollText } from 'lucide-react'
import api, { list } from '../../lib/api'
import { full } from '../../lib/format'
import { Card, Empty, PageHeader, Spinner, Table } from '../../components/ui'

export default function Audit() {
  const [rows, setRows] = useState(null)
  useEffect(() => { api.get('/admin/audit/', { params: { page_size: 300 } }).then((r) => setRows(list(r.data))) }, [])
  return (
    <>
      <PageHeader title="Audit trail" subtitle="Every configuration change and officer decision, with who made it and when (Art. 5(2) accountability)." />
      <Card>
        {rows === null ? <Spinner /> : (
          <Table rows={rows} empty={<Empty icon={ScrollText} title="No changes recorded yet" />} columns={[
            { key: 't', label: 'When', className: 'whitespace-nowrap', render: (r) => <span className="tabular text-xs text-ink-2">{full(r.created_at)}</span> },
            { key: 'a', label: 'Who', render: (r) => <span className="font-medium">{r.actor}</span> },
            { key: 'x', label: 'Action', render: (r) => <span className="font-mono text-xs text-accent">{r.action}</span> },
            { key: 'g', label: 'Target', render: (r) => <span className="text-ink-2">{r.target}</span> },
            { key: 'd', label: 'Details', render: (r) => <span className="line-clamp-2 max-w-md break-all font-mono text-[11px] text-ink-3">{JSON.stringify(r.details)}</span> },
          ]} />
        )}
      </Card>
    </>
  )
}
