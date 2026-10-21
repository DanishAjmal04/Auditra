import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'

function getDaysRemaining(deadline) {
  const now = new Date()
  const end = new Date(deadline)
  return Math.ceil((end - now) / (1000 * 60 * 60 * 24))
}

const rightColor = {
  ACCESS: '#3182ce',
  RECTIFICATION: '#805ad5',
  ERASURE: '#e53e3e',
  RESTRICTION: '#dd6b20',
  PORTABILITY: '#38a169',
  OBJECTION: '#d69e2e'
}

const statusColor = {
  PENDING: { bg: '#fff0f0', text: '#e53e3e' },
  IN_PROGRESS: { bg: '#fff8e1', text: '#dd6b20' },
  COMPLETED: { bg: '#f0fff4', text: '#38a169' }
}

export default function SubjectAccess() {
  const [requests, setRequests] = useState([])
  const [filter, setFilter] = useState('ALL')
  const [error, setError] = useState('')

  function loadRequests() {
    api.get('/subject-access-requests/')
      .then(response => {
        setRequests(response.data)
        setError('')
      })
      .catch(() => setError('Could not load subject-access requests.'))
  }

  useEffect(() => {
    loadRequests()
  }, [])

  function updateStatus(requestRow, status) {
    api.patch(`/subject-access-requests/${requestRow.id}/`, { status })
      .then(() => loadRequests())
      .catch(() => setError('Could not update that request.'))
  }

  const overdue = requests.filter(r =>
    getDaysRemaining(r.deadline) < 0 && r.status !== 'COMPLETED'
  ).length

  const filtered = requests.filter(r => {
    if (filter === 'ALL') return true
    if (filter === 'OVERDUE') return getDaysRemaining(r.deadline) < 0 && r.status !== 'COMPLETED'
    return r.status === filter
  })

  function getCountdown(req) {
    if (req.status === 'COMPLETED') return { text: 'Completed', color: '#38a169' }
    const days = getDaysRemaining(req.deadline)
    if (days < 0) return { text: `${Math.abs(days)}d overdue`, color: '#e53e3e' }
    if (days === 0) return { text: 'Due today!', color: '#e53e3e' }
    if (days <= 7) return { text: `${days}d left`, color: '#dd6b20' }
    return { text: `${days}d left`, color: '#38a169' }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="compliance" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
            Subject Access Requests
          </h1>
          <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
            GDPR Art. 15–21 — All requests must be responded to within 30 days.
          </p>
        </div>
        {error && <p style={{ color: '#e53e3e', marginBottom: 12 }}>{error}</p>}

        {/* Summary Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          marginBottom: 24
        }}>
          {[
            { label: 'TOTAL REQUESTS', value: requests.length, color: '#3182ce' },
            { label: 'OVERDUE', value: overdue, color: '#e53e3e' },
            { label: 'IN PROGRESS', value: requests.filter(r => r.status === 'IN_PROGRESS').length, color: '#dd6b20' },
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

        {/* Overdue Alert */}
        {overdue > 0 && (
          <div style={{
            background: '#fff0f0', border: '1px solid #feb2b2',
            borderRadius: 10, padding: '14px 18px',
            marginBottom: 20, display: 'flex',
            alignItems: 'center', gap: 12
          }}>
            <span style={{ fontSize: 20 }}>⚠️</span>
            <p style={{ margin: 0, fontWeight: 600, color: '#e53e3e', fontSize: 14 }}>
              {overdue} request(s) are overdue — immediate action required under GDPR Art. 12.
            </p>
          </div>
        )}

        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {['ALL', 'OVERDUE', 'PENDING', 'IN_PROGRESS', 'COMPLETED'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 14px', borderRadius: 6,
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
                {['Subject', 'Right Type', 'Received', 'Deadline', 'Countdown', 'Status'].map(h => (
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
                const countdown = getCountdown(req)
                return (
                  <tr key={req.id} style={{
                    borderBottom: '1px solid #f0f0f0',
                    background: getDaysRemaining(req.deadline) < 0 && req.status !== 'COMPLETED'
                      ? '#fff0f0' : 'white'
                  }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600 }}>
                      {req.subject_id}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontSize: 11, padding: '3px 8px', borderRadius: 4,
                        background: (rightColor[req.right_type] || '#888') + '20',
                        color: rightColor[req.right_type] || '#888',
                        fontWeight: 600
                      }}>
                        {req.right_type}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', color: '#555' }}>
                      {req.received_at}
                    </td>
                    <td style={{ padding: '12px 14px', color: '#555' }}>
                      {req.deadline}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontWeight: 700,
                        color: countdown.color,
                        fontSize: 13
                      }}>
                        {countdown.text}
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
                          border: `1px solid ${statusColor[req.status]?.text || '#ddd'}`,
                          color: statusColor[req.status]?.text || '#666',
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