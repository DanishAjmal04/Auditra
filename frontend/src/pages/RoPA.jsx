import { useCallback, useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import api from '../utils/axios'


const emptyForm = {
  activity_name: '',
  purpose: '',
  legal_basis: 'CONSENT',
  data_categories: '',
  retention_period: '',
  security_measures: '',
}


const legalBases = [
  ['CONSENT', 'Consent'],
  ['CONTRACT', 'Contract'],
  ['LEGAL_OBLIGATION', 'Legal obligation'],
  ['VITAL_INTEREST', 'Vital interest'],
  ['PUBLIC_TASK', 'Public task'],
  ['LEGITIMATE_INTEREST', 'Legitimate interest'],
]


const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #d9dee7',
  borderRadius: 7,
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
}


export default function RoPA() {
  const [activities, setActivities] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [search, setSearch] = useState('')
  const [legalBasis, setLegalBasis] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const fetchActivities = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/processing-activities/', {
        params: {
          search: search || undefined,
          legal_basis: legalBasis || undefined,
        },
      })
      setActivities(data)
    } catch {
      setError('Processing activities could not be loaded.')
    } finally {
      setLoading(false)
    }
  }, [search, legalBasis])

  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  function updateField(event) {
    const { name, value } = event.target
    setForm(current => ({ ...current, [name]: value }))
  }

  function startCreate() {
    setForm(emptyForm)
    setEditingId(null)
    setMessage('')
    setError('')
    setShowForm(true)
  }

  function startEdit(activity) {
    setForm({
      activity_name: activity.activity_name,
      purpose: activity.purpose,
      legal_basis: activity.legal_basis,
      data_categories: activity.data_categories,
      retention_period: activity.retention_period,
      security_measures: activity.security_measures,
    })
    setEditingId(activity.id)
    setMessage('')
    setError('')
    setShowForm(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function closeForm() {
    setShowForm(false)
    setEditingId(null)
    setForm(emptyForm)
  }

  async function saveActivity(event) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')

    try {
      if (editingId) {
        await api.patch(`/processing-activities/${editingId}/`, form)
        setMessage('Processing activity updated.')
      } else {
        await api.post('/processing-activities/', form)
        setMessage('Processing activity added to RoPA.')
      }
      closeForm()
      await fetchActivities()
    } catch (requestError) {
      const details = requestError.response?.data
      setError(
        details
          ? Object.values(details).flat().join(' ')
          : 'Processing activity could not be saved.'
      )
    } finally {
      setSaving(false)
    }
  }

  async function deleteActivity(activity) {
    const confirmed = window.confirm(
      `Delete "${activity.activity_name}" from the RoPA register?`
    )
    if (!confirmed) return

    setMessage('')
    setError('')
    try {
      await api.delete(`/processing-activities/${activity.id}/`)
      setMessage('Processing activity deleted.')
      await fetchActivities()
    } catch {
      setError('Processing activity could not be deleted.')
    }
  }

  const basisLabel = Object.fromEntries(legalBases)

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="compliance" />

      <main style={{ flex: 1, overflow: 'auto', padding: 32 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 24,
        }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
              Records of Processing Activities
            </h1>
            <p style={{ color: '#667085', fontSize: 14, marginTop: 6 }}>
              GDPR Article 30 — maintain the organization’s processing register.
            </p>
          </div>
          <button onClick={startCreate} style={{
            background: '#1a1a2e',
            color: 'white',
            border: 0,
            borderRadius: 8,
            padding: '11px 18px',
            fontWeight: 600,
            cursor: 'pointer',
          }}>
            Add processing activity
          </button>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          marginBottom: 20,
        }}>
          {[
            ['REGISTERED ACTIVITIES', activities.length, '#3182ce'],
            ['LEGAL BASES IN VIEW', new Set(activities.map(item => item.legal_basis)).size, '#805ad5'],
            ['ARTICLE', '30', '#38a169'],
          ].map(([label, value, color]) => (
            <div key={label} style={{
              background: 'white',
              borderRadius: 12,
              padding: 20,
              borderTop: `4px solid ${color}`,
            }}>
              <p style={{ fontSize: 11, color: '#667085', letterSpacing: 1, margin: '0 0 8px' }}>
                {label}
              </p>
              <p style={{ fontSize: 32, fontWeight: 700, color, margin: 0 }}>{value}</p>
            </div>
          ))}
        </div>

        {showForm && (
          <form onSubmit={saveActivity} style={{
            background: 'white',
            borderRadius: 12,
            padding: 24,
            marginBottom: 20,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 style={{ fontSize: 16, margin: 0 }}>
                {editingId ? 'Edit processing activity' : 'New processing activity'}
              </h2>
              <button type="button" onClick={closeForm} style={{
                border: 0, background: 'transparent', color: '#667085', cursor: 'pointer'
              }}>
                Close
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                Activity name
                <input name="activity_name" value={form.activity_name} onChange={updateField} required style={{ ...inputStyle, marginTop: 6 }} />
              </label>
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                Purpose
                <input name="purpose" value={form.purpose} onChange={updateField} required style={{ ...inputStyle, marginTop: 6 }} />
              </label>
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                Legal basis
                <select name="legal_basis" value={form.legal_basis} onChange={updateField} style={{ ...inputStyle, marginTop: 6 }}>
                  {legalBases.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                Retention period
                <input name="retention_period" value={form.retention_period} onChange={updateField} required placeholder="e.g. 7 years" style={{ ...inputStyle, marginTop: 6 }} />
              </label>
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                Data categories
                <textarea name="data_categories" value={form.data_categories} onChange={updateField} required rows={3} style={{ ...inputStyle, marginTop: 6, resize: 'vertical' }} />
              </label>
              <label style={{ fontSize: 13, fontWeight: 600 }}>
                Security measures
                <textarea name="security_measures" value={form.security_measures} onChange={updateField} required rows={3} style={{ ...inputStyle, marginTop: 6, resize: 'vertical' }} />
              </label>
            </div>

            <button type="submit" disabled={saving} style={{
              marginTop: 20,
              background: saving ? '#98a2b3' : '#1a1a2e',
              color: 'white',
              border: 0,
              borderRadius: 8,
              padding: '10px 18px',
              fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer',
            }}>
              {saving ? 'Saving...' : editingId ? 'Update activity' : 'Add to RoPA'}
            </button>
          </form>
        )}

        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: 12,
          marginBottom: 16,
        }}>
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search activity, purpose, or data category..."
            style={inputStyle}
          />
          <select value={legalBasis} onChange={event => setLegalBasis(event.target.value)} style={inputStyle}>
            <option value="">All legal bases</option>
            {legalBases.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {message && <p style={{ color: '#2f855a', fontSize: 14 }}>{message}</p>}
        {error && <p style={{ color: '#c53030', fontSize: 14 }}>{error}</p>}

        <div style={{ background: 'white', borderRadius: 12, overflow: 'hidden' }}>
          {loading ? (
            <p style={{ padding: 24 }}>Loading processing activities...</p>
          ) : activities.length === 0 ? (
            <p style={{ padding: 24, color: '#667085' }}>No matching processing activities found.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  {['Activity', 'Purpose', 'Legal basis', 'Data categories', 'Retention', 'Security measures', 'Actions'].map(header => (
                    <th key={header} style={{
                      padding: '12px 14px',
                      textAlign: 'left',
                      color: '#667085',
                      fontSize: 11,
                      letterSpacing: 0.4,
                    }}>
                      {header.toUpperCase()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {activities.map(activity => (
                  <tr key={activity.id} style={{ borderTop: '1px solid #eef0f3' }}>
                    <td style={{ padding: '13px 14px', fontWeight: 600 }}>{activity.activity_name}</td>
                    <td style={{ padding: '13px 14px' }}>{activity.purpose}</td>
                    <td style={{ padding: '13px 14px' }}>
                      <span style={{
                        background: '#ebf8ff', color: '#2b6cb0', padding: '3px 7px',
                        borderRadius: 4, fontSize: 11, fontWeight: 600,
                      }}>
                        {basisLabel[activity.legal_basis] || activity.legal_basis}
                      </span>
                    </td>
                    <td style={{ padding: '13px 14px', maxWidth: 180 }}>{activity.data_categories}</td>
                    <td style={{ padding: '13px 14px' }}>{activity.retention_period}</td>
                    <td style={{ padding: '13px 14px', maxWidth: 200 }}>{activity.security_measures}</td>
                    <td style={{ padding: '13px 14px', whiteSpace: 'nowrap' }}>
                      <button onClick={() => startEdit(activity)} style={{
                        border: '1px solid #3182ce', background: 'white', color: '#3182ce',
                        borderRadius: 5, padding: '5px 9px', marginRight: 6, cursor: 'pointer',
                      }}>
                        Edit
                      </button>
                      <button onClick={() => deleteActivity(activity)} style={{
                        border: '1px solid #e53e3e', background: 'white', color: '#e53e3e',
                        borderRadius: 5, padding: '5px 9px', cursor: 'pointer',
                      }}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  )
}
