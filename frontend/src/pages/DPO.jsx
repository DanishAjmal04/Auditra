import { useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import api from '../utils/axios'


const emptyForm = {
  organization_name: '',
  dpo_required: true,
  name: '',
  contact: '',
  designated_at: '',
  scope: '',
  independent: false,
  direct_access_to_management: false,
  conflict_free: false,
  published_contact_details: false,
}


const statusMeta = {
  COMPLIANT: { label: 'Compliant', color: '#2f855a', background: '#f0fff4' },
  MISSING: { label: 'DPO Missing', color: '#c53030', background: '#fff5f5' },
  REVIEW_REQUIRED: { label: 'Review Required', color: '#b7791f', background: '#fffff0' },
  NOT_REQUIRED: { label: 'DPO Not Required', color: '#2b6cb0', background: '#ebf8ff' },
}


const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #d9dee7',
  borderRadius: 7,
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
}


export default function DPO() {
  const [form, setForm] = useState(emptyForm)
  const [status, setStatus] = useState('MISSING')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/dpo/')
      .then(({ data }) => {
        setForm({
          ...emptyForm,
          ...data,
          designated_at: data.designated_at || '',
        })
        setStatus(data.compliance_status)
      })
      .catch(() => setError('DPO record could not be loaded.'))
      .finally(() => setLoading(false))
  }, [])

  function updateField(event) {
    const { name, type, checked, value } = event.target
    setForm(current => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }))
    setMessage('')
  }

  async function saveDesignation(event) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')

    const payload = Object.fromEntries(
      Object.keys(emptyForm).map(key => [key, form[key]])
    )
    payload.designated_at = payload.designated_at || null

    try {
      const { data } = await api.put('/dpo/', payload)
      setForm({
        ...emptyForm,
        ...data,
        designated_at: data.designated_at || '',
      })
      setStatus(data.compliance_status)
      setMessage('DPO designation record saved and verified.')
    } catch (requestError) {
      const details = requestError.response?.data
      setError(
        details
          ? Object.values(details).flat().join(' ')
          : 'DPO record could not be saved.'
      )
    } finally {
      setSaving(false)
    }
  }

  const meta = statusMeta[status] || statusMeta.REVIEW_REQUIRED
  const detailsDisabled = !form.dpo_required

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="compliance" />

      <main style={{ flex: 1, overflow: 'auto', padding: 32 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
              DPO Designation Verification
            </h1>
            <p style={{ color: '#667085', fontSize: 14, marginTop: 6 }}>
              GDPR Articles 37–39 — record and verify Data Protection Officer controls.
            </p>
          </div>
          <div style={{
            padding: '9px 14px',
            borderRadius: 20,
            color: meta.color,
            background: meta.background,
            fontSize: 13,
            fontWeight: 700,
            border: `1px solid ${meta.color}30`,
          }}>
            {meta.label}
          </div>
        </div>

        {loading ? (
          <div style={{ background: 'white', padding: 24, borderRadius: 12 }}>
            Loading DPO record...
          </div>
        ) : (
          <form onSubmit={saveDesignation} style={{ maxWidth: 980 }}>
            <section style={{
              background: 'white',
              padding: 24,
              borderRadius: 12,
              marginBottom: 20,
            }}>
              <h2 style={{ fontSize: 16, margin: '0 0 20px' }}>Designation details</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>
                  Organization name
                  <input
                    name="organization_name"
                    value={form.organization_name}
                    onChange={updateField}
                    required
                    style={{ ...inputStyle, marginTop: 6 }}
                  />
                </label>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  fontSize: 14,
                  paddingTop: 25,
                }}>
                  <input
                    type="checkbox"
                    name="dpo_required"
                    checked={form.dpo_required}
                    onChange={updateField}
                  />
                  A DPO is required for this organization
                </label>
                <label style={{ fontSize: 13, fontWeight: 600 }}>
                  DPO name
                  <input
                    name="name"
                    value={form.name}
                    onChange={updateField}
                    disabled={detailsDisabled}
                    style={{ ...inputStyle, marginTop: 6 }}
                  />
                </label>
                <label style={{ fontSize: 13, fontWeight: 600 }}>
                  DPO email
                  <input
                    type="email"
                    name="contact"
                    value={form.contact}
                    onChange={updateField}
                    disabled={detailsDisabled}
                    style={{ ...inputStyle, marginTop: 6 }}
                  />
                </label>
                <label style={{ fontSize: 13, fontWeight: 600 }}>
                  Designation date
                  <input
                    type="date"
                    name="designated_at"
                    value={form.designated_at}
                    onChange={updateField}
                    disabled={detailsDisabled}
                    style={{ ...inputStyle, marginTop: 6 }}
                  />
                </label>
              </div>

              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginTop: 18 }}>
                DPO scope
                <textarea
                  name="scope"
                  value={form.scope}
                  onChange={updateField}
                  disabled={detailsDisabled}
                  rows={3}
                  style={{ ...inputStyle, marginTop: 6, resize: 'vertical' }}
                />
              </label>
            </section>

            <section style={{
              background: 'white',
              padding: 24,
              borderRadius: 12,
              marginBottom: 20,
            }}>
              <h2 style={{ fontSize: 16, margin: '0 0 8px' }}>Verification checklist</h2>
              <p style={{ color: '#667085', fontSize: 13, margin: '0 0 18px' }}>
                All controls must be confirmed for a compliant designation.
              </p>
              {[
                ['independent', 'The DPO can perform duties independently'],
                ['direct_access_to_management', 'The DPO reports directly to the highest management level'],
                ['conflict_free', 'No conflict of interest has been identified'],
                ['published_contact_details', 'DPO contact details are published and accessible'],
              ].map(([name, label]) => (
                <label key={name} style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                  padding: '10px 0',
                  fontSize: 14,
                  borderBottom: '1px solid #f0f1f3',
                }}>
                  <input
                    type="checkbox"
                    name={name}
                    checked={form[name]}
                    onChange={updateField}
                    disabled={detailsDisabled}
                  />
                  {label}
                </label>
              ))}
            </section>

            {message && <p style={{ color: '#2f855a', fontSize: 14 }}>{message}</p>}
            {error && <p style={{ color: '#c53030', fontSize: 14 }}>{error}</p>}
            <button type="submit" disabled={saving} style={{
              background: saving ? '#98a2b3' : '#1a1a2e',
              color: 'white',
              border: 0,
              borderRadius: 8,
              padding: '11px 20px',
              fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer',
            }}>
              {saving ? 'Saving...' : 'Save and verify'}
            </button>
          </form>
        )}
      </main>
    </div>
  )
}
