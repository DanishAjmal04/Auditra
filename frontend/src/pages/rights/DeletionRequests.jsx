import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'


function getDaysRemaining(deadline) {
  const now = new Date()
  const end = new Date(deadline)
  return Math.ceil((end - now) / (1000 * 60 * 60 * 24))
}

export default function DeletionRequests() {
  const [requests, setRequests] = useState([])
  const [filter, setFilter] = useState('ALL')
  const [error, setError] = useState('')

  function loadRequests() {
    api.get('/deletion-requests/')
      .then(response => {
        setRequests(response.data)
        setError('')
      })
      .catch(() => setError('Could not load deletion requests.'))
  }

  useEffect(() => {
    loadRequests()
  }, [])

  function updateStatus(requestRow, status) {
    api.patch(`/deletion-requests/${requestRow.id}/`, { status })
      .then(() => loadRequests())
      .catch(() => setError('Could not update that request.'))
  }

  const filtered = requests.filter(r => {
    if (filter === 'ALL') return true
    if (filter === 'OVERDUE') return getDaysRemaining(r.deadline) < 0 && r.status !== 'COMPLETED'
    if (filter === 'URGENT') {
      const d = getDaysRemaining(r.deadline)
      return d >= 0 && d <= 5 && r.status !== 'COMPLETED'
    }
    return r.status === filter
  })

  const overdue = requests.filter(r => getDaysRemaining(r.deadline) < 0 && r.status !== 'COMPLETED').length
  const urgent = requests.filter(r => {
    const d = getDaysRemaining(r.deadline)
    return d >= 0 && d <= 5 && r.status !== 'COMPLETED'
  }).length
  const pending = requests.filter(r => r.status === 'PENDING').length
  const completed = requests.filter(r => r.status === 'COMPLETED').length

  function getRowStyle(req) {
    const days = getDaysRemaining(req.deadline)
    if (req.status === 'COMPLETED') return '#f0fff4'
    if (days < 0) return '#fff0f0'
    if (days <= 5) return '#fff8e1'
    return 'white'
  }

  function getDaysLabel(req) {
    if (req.status === 'COMPLETED') return { text: 'Completed', color: '#38a169' }
    const days = getDaysRemaining(req.deadline)
    if (days < 0) return { text: `${Math.abs(days)} days overdue`, color: '#e53e3e' }
    if (days === 0) return { text: 'Due today', color: '#e53e3e' }
    if (days <= 5) return { text: `${days} days left`, color: '#dd6b20' }
    return { text: `${days} days left`, color: '#38a169' }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="compliance" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
            Deletion Requests
          </h1>
          <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
            GDPR Art. 17 — Right to Erasure. Requests must be fulfilled within 30 days.
          </p>
        </div>
        {error && <p style={{ color: '#e53e3e', marginBottom: 12 }}>{error}</p>}

        {/* Summary Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 16,
          marginBottom: 24
        }}>
          {[
            { label: 'OVERDUE', value: overdue, color: '#e53e3e' },
            { label: 'URGENT (≤5 days)', value: urgent, color: '#dd6b20' },
            { label: 'PENDING', value: pending, color: '#3182ce' },
            { label: 'COMPLETED', value: completed, color: '#38a169' },
          ].map(card => (
            <div key={card.label} style={{
              background: 'white', borderRadius: 12,
              padding: 20, borderTop: `4px solid ${card.color}`
            }}>
              <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>
                {card.label}
              </p>
              <p style={{ fontSize: 36, fontWeight: 700, color: card.color, margin: 0 }}>
                {card.value}
              </p>
            </div>
          ))}
        </div>

        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {['ALL', 'OVERDUE', 'URGENT', 'PENDING', 'IN_PROGRESS', 'COMPLETED'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                border: '1px solid',
                borderColor: filter === f ? '#1a1a2e' : '#ddd',
                background: filter === f ? '#1a1a2e' : 'white',
                color: filter === f ? 'white' : '#555',
                fontSize: 12,
                fontWeight: filter === f ? 600 : 400,
                cursor: 'pointer'
              }}
            >
              {f.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Table */}
        <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                {['Subject ID', 'Received', 'Deadline', 'Days Remaining', 'Status'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '8px 14px',
                    fontSize: 11, color: '#666',
                    letterSpacing: 0.5, fontWeight: 600
                  }}>
                    {h.toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(req => {
                const daysLabel = getDaysLabel(req)
                return (
                  <tr key={req.id} style={{ background: getRowStyle(req) }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600 }}>
                      {req.subject_id}
                    </td>
                    <td style={{ padding: '12px 14px', color: '#555' }}>
                      {req.received_at_date || req.received_at}
                    </td>
                    <td style={{ padding: '12px 14px', color: '#555' }}>
                      {req.deadline}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontWeight: 700,
                        color: daysLabel.color,
                        fontSize: 13
                      }}>
                        {daysLabel.text}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <select
                        value={req.status}
                        onChange={event => updateStatus(req, event.target.value)}
                        style={{
                          fontSize: 12,
                          padding: '4px 8px',
                          borderRadius: 4,
                          border: '1px solid #ddd',
                        }}
                      >
                        <option value="PENDING">Pending</option>
                        <option value="IN_PROGRESS">In progress</option>
                        <option value="COMPLETED">Completed</option>
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p style={{ textAlign: 'center', color: '#666', padding: 32 }}>
              No requests found.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}