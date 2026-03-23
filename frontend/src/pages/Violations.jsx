import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

const API = 'http://127.0.0.1:8000/api'
const severityColor = { CRITICAL: '#e53e3e', HIGH: '#dd6b20', MEDIUM: '#d69e2e', LOW: '#38a169' }
const statusColor = { OPEN: '#e53e3e', REVIEWING: '#d69e2e', RESOLVED: '#38a169' }

export default function Violations() {
  const [violations, setViolations] = useState([])
  const [filter, setFilter] = useState('')

  useEffect(() => { fetchViolations() }, [filter])

  function fetchViolations() {
    const params = filter ? `?severity=${filter}` : ''
    axios.get(`${API}/violations/${params}`).then(r => setViolations(r.data))
  }

  function updateStatus(id, status) {
    axios.patch(`${API}/violations/${id}/status/`, { status })
      .then(() => fetchViolations())
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      {/* Sidebar */}
      <div style={{
        width: 220, background: '#1a1a2e', color: 'white',
        display: 'flex', flexDirection: 'column', padding: '24px 0'
      }}>
        <div style={{ padding: '0 24px 24px', borderBottom: '1px solid #2d2d44' }}>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Auditra</h2>
          <p style={{ fontSize: 10, color: '#8892b0', letterSpacing: 1.5 }}>COMPLIANCE MONITOR</p>
        </div>
        <nav style={{ padding: '16px 0', flex: 1 }}>
          <p style={{ padding: '8px 24px', fontSize: 10, color: '#8892b0', letterSpacing: 1.5 }}>MONITOR</p>
          <Link to="/dashboard" style={{
            display: 'block', padding: '10px 24px',
            color: '#8892b0', textDecoration: 'none', fontSize: 14
          }}>Dashboard</Link>
          <Link to="/violations" style={{
            display: 'block', padding: '10px 24px',
            color: 'white', textDecoration: 'none', background: '#2d2d44', fontSize: 14
          }}>Violations</Link>
        </nav>
      </div>

      {/* Main */}
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>Violations Log</h1>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{
              padding: '6px 16px', borderRadius: 20, border: 'none',
              background: filter === s ? '#1a1a2e' : 'white',
              color: filter === s ? 'white' : '#666',
              fontSize: 13, cursor: 'pointer', fontWeight: filter === s ? 600 : 400
            }}>
              {s || 'All'}
            </button>
          ))}
        </div>

        {/* Table */}
        <div style={{ background: 'white', borderRadius: 12, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8f9fa' }}>
                {['#', 'Timestamp', 'User', 'Violation', 'GDPR Article', 'Severity', 'AI Score', 'Anomaly', 'Status'].map(h => (
                  <th key={h} style={{
                    padding: '12px 16px', textAlign: 'left',
                    fontSize: 11, color: '#666', fontWeight: 600, letterSpacing: 0.5
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {violations.map((v, i) => (
                <tr key={v.id} style={{ borderTop: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px 16px', fontSize: 13, color: '#999' }}>
                    {String(i + 1).padStart(3, '0')}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 13 }}>
                    {new Date(v.log.timestamp).toLocaleString()}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 500 }}>
                    {v.log.user_id}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 13, maxWidth: 200 }}>
                    {v.explanation}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 12 }}>
                    <span style={{
                      background: '#e8f0fe', color: '#1a73e8',
                      padding: '2px 8px', borderRadius: 4, fontWeight: 500
                    }}>{v.rule.gdpr_article}</span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                      background: severityColor[v.rule.severity] + '20',
                      color: severityColor[v.rule.severity]
                    }}>{v.rule.severity}</span>
                  </td>
                  <td style={{
                    padding: '12px 16px', fontSize: 13, fontWeight: 700,
                    color: v.risk_score > 0.8 ? '#e53e3e' : v.risk_score > 0.6 ? '#dd6b20' : '#38a169'
                  }}>
                    {v.risk_score.toFixed(2)}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 13 }}>
                    {v.is_anomaly
                      ? <span style={{ color: '#e53e3e', fontWeight: 600 }}>Yes</span>
                      : <span style={{ color: '#999' }}>No</span>}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <select
                      value={v.status}
                      onChange={e => updateStatus(v.id, e.target.value)}
                      style={{
                        fontSize: 12, padding: '4px 8px', borderRadius: 4,
                        border: `1px solid ${statusColor[v.status]}`,
                        color: statusColor[v.status], cursor: 'pointer', outline: 'none'
                      }}
                    >
                      <option value="OPEN">Open</option>
                      <option value="REVIEWING">Reviewing</option>
                      <option value="RESOLVED">Resolved</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}