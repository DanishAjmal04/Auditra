import { useCallback, useEffect, useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import api, { errorText, list } from '../lib/api'
import { Button, Card, CardHeader, Checkbox, Empty, ErrorNote, Field, Input, Modal, Select, Spinner, Table, Textarea } from './ui'

/* Generic list + create/edit/delete for a REST collection.
   fields: [{ name, label, type: text|textarea|select|checkbox|datetime|date|number|multiselect, options, hint, required }] */

function toInput(field, value) {
  if (value === null || value === undefined) return field.type === 'checkbox' ? false : field.type === 'multiselect' ? [] : ''
  if (field.type === 'datetime') return value ? new Date(value).toISOString().slice(0, 16) : ''
  if (field.type === 'time') return String(value).slice(0, 5)
  return value
}

function fromInput(field, value) {
  if (field.type === 'datetime') return value ? new Date(value).toISOString() : null
  if (field.type === 'number') return value === '' ? null : Number(value)
  if ((field.type === 'select' || field.type === 'date') && value === '') return field.nullable ? null : ''
  return value
}

export function RecordForm({ fields, values, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {fields.map((f) => {
        const value = values[f.name]
        const set = (v) => onChange({ ...values, [f.name]: v })
        const span = f.half ? '' : 'col-span-2'
        if (f.type === 'checkbox') {
          return <Checkbox key={f.name} className={span} label={f.label} checked={Boolean(value)} onChange={(e) => set(e.target.checked)} />
        }
        if (f.type === 'multiselect') {
          const entries = Object.entries(f.options)
          return (
            <Field key={f.name} label={f.label} hint={f.hint} className={span}>
              <div className="grid grid-cols-2 gap-1.5 rounded-lg border border-line-2 bg-canvas p-2.5">
                {entries.map(([key, label]) => (
                  <Checkbox key={key} label={label} checked={(value || []).includes(key)}
                    onChange={(e) => set(e.target.checked ? [...(value || []), key] : (value || []).filter((v) => v !== key))} />
                ))}
              </div>
            </Field>
          )
        }
        return (
          <Field key={f.name} label={f.label} hint={f.hint} className={span}>
            {f.type === 'textarea' ? <Textarea value={value} onChange={(e) => set(e.target.value)} />
              : f.type === 'select' ? <Select value={value ?? ''} options={f.options} placeholder={f.placeholder ?? (f.nullable ? '—' : undefined)} onChange={(e) => set(e.target.value)} />
                : <Input type={f.type === 'datetime' ? 'datetime-local' : f.type || 'text'} value={value} placeholder={f.placeholder} onChange={(e) => set(e.target.value)} />}
          </Field>
        )
      })}
    </div>
  )
}

export function useCollection(path, deps = []) {
  const [rows, setRows] = useState(null)
  const reload = useCallback(() => api.get(path, { params: { page_size: 500 } }).then((r) => setRows(list(r.data))), [path])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload() }, [reload, ...deps])
  return [rows, reload]
}

export default function Crud({ title, subtitle, icon, path, fields, columns, defaults = {}, canDelete = true, canCreate = true,
  deps = [], extraActions, emptyText, onSaved }) {
  const [rows, reload] = useCollection(path, deps)
  const [editing, setEditing] = useState(null)
  const [values, setValues] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function open(row) {
    const initial = {}
    fields.forEach((f) => { initial[f.name] = toInput(f, row ? row[f.name] : (defaults[f.name] ?? (f.type === 'multiselect' ? [] : ''))) })
    setValues(initial)
    setEditing(row || 'new')
    setError('')
  }

  async function save() {
    setBusy(true)
    setError('')
    const payload = {}
    fields.forEach((f) => { payload[f.name] = fromInput(f, values[f.name]) })
    try {
      if (editing === 'new') await api.post(path, payload)
      else await api.patch(`${path}${editing.id}/`, payload)
      setEditing(null)
      await reload()
      onSaved?.()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  async function remove(row) {
    if (!window.confirm('Delete this record? This cannot be undone.')) return
    try {
      await api.delete(`${path}${row.id}/`)
      reload()
      onSaved?.()
    } catch (e) {
      window.alert(errorText(e))
    }
  }

  const actionColumn = {
    key: '_actions', label: '', className: 'w-24 text-right', render: (row) => (
      <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
        {extraActions?.(row, reload)}
        <Button size="sm" variant="ghost" icon={Pencil} onClick={() => open(row)} title="Edit" />
        {canDelete && <Button size="sm" variant="ghost" icon={Trash2} onClick={() => remove(row)} title="Delete" />}
      </div>
    ),
  }

  return (
    <Card>
      <CardHeader icon={icon} title={title} subtitle={subtitle}
        actions={canCreate && <Button size="sm" variant="primary" icon={Plus} onClick={() => open(null)}>Add</Button>} />
      {rows === null ? <Spinner /> : (
        <Table columns={[...columns, actionColumn]} rows={rows} empty={<Empty title={emptyText || 'Nothing recorded yet'} />} />
      )}
      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={editing === 'new' ? `Add ${title.toLowerCase()}` : `Edit ${title.toLowerCase()}`}
        width="max-w-2xl"
        footer={<><Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button><Button variant="primary" loading={busy} onClick={save}>Save</Button></>}>
        <RecordForm fields={fields} values={values} onChange={setValues} />
        <div className="mt-3"><ErrorNote>{error}</ErrorNote></div>
      </Modal>
    </Card>
  )
}
