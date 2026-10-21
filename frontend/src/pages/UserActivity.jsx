import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Sidebar from '../components/Sidebar'
import AlertBanner from '../components/AlertBanner'
import api, { downloadAuthenticated } from '../utils/axios'

const severityColor = {
  CRITICAL: '#e53e3e',
  HIGH: '#dd6b20',
  MEDIUM: '#d69e2e',
  LOW: '#38a169',
}

const statusColor = {
  OPEN: { bg: '#fff0f0', text: '#e53e3e' },
  REVIEWING: { bg: '#fff8e1', text: '#dd6b20' },
  RESOLVED: { bg: '#f0fff4', text: '#38a169' },
}

export default function UserActivity() {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [userData, setUserData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/users/')
      .then(response => {
        const ids = response.data
        setUsers(ids)
        setSelectedUser(ids[0] || '')
        setError(ids.length ? '' : 'No monitored users yet. Load logs or the anomaly demo.')
      })
      .catch(() => {
        setUsers([])
        setError('Could not load users.')
      })
  }, [])

  useEffect(() => {
    if (!selectedUser) {
      setUserData(null)
      return
    }
    setLoading(true)
    api.get(`/user-activity/?user_id=${encodeURIComponent(selectedUser)}`)
      .then(response => {
        setUserData(response.data)
        setError('')
        setLoading(false)
      })
      .catch(() => {
        setUserData(null)
        setError('Could not load activity for this user.')
        setLoading(false)
      })
  }, [selectedUser])

  async function downloadReport() {
    try {
      await downloadAuthenticated(
        `/user-pdf/${encodeURIComponent(selectedUser)}/`,
        `auditra-${selectedUser}.pdf`,
      )
    } catch {
      setError('Could not download the user report.')
    }
  }

  const anomaly = userData?.anomaly

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <AlertBanner />
      <Sidebar role="compliance" />

      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 28,
          gap: 12,
        }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>User Activity</h1>
          <select
            value={selectedUser}
            onChange={event => setSelectedUser(event.target.value)}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: '1px solid #ddd',
              fontSize: 14,
              background: 'white',
              cursor: 'pointer',
              minWidth: 180,
            }}
          >
            {users.map(user => (
              <option key={user} value={user}>{user}</option>
            ))}
          </select>
          <button
            onClick={downloadReport}
            disabled={!selectedUser}
            style={{
              padding: '8px 18px',
              background: selectedUser ? '#1a1a2e' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: selectedUser ? 'pointer' : 'not-allowed',
            }}
          >
            Download Report
          </button>
        </div>

        {error && <p style={{ color: '#e53e3e', marginBottom: 16 }}>{error}</p>}

        {loading && (
          <div style={{ textAlign: 'center', padding: 60, color: '#666' }}>
            Loading user data...
          </div>
        )}

        {!loading && userData && (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 16,
              marginBottom: 24,
            }}>
              <div style={{ background: 'white', borderRadius: 12, padding: 20, borderTop: '4px solid #e53e3e' }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>TOTAL VIOLATIONS</p>
                <p style={{ fontSize: 36, fontWeight: 700, color: '#e53e3e', margin: 0 }}>{userData.total_violations}</p>
              </div>
              <div style={{ background: 'white', borderRadius: 12, padding: 20, borderTop: '4px solid #dd6b20' }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>AVG RISK SCORE</p>
                <p style={{ fontSize: 36, fontWeight: 700, color: '#dd6b20', margin: 0 }}>{userData.avg_risk_score}</p>
              </div>
              <div style={{ background: 'white', borderRadius: 12, padding: 20, borderTop: '4px solid #3182ce' }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>MOST COMMON</p>
                <p style={{ fontSize: 28, fontWeight: 700, color: '#3182ce', margin: 0 }}>{userData.most_common}</p>
              </div>
              <div style={{ background: 'white', borderRadius: 12, padding: 20, borderTop: '4px solid #805ad5' }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>ANOMALY SCORE</p>
                <p style={{ fontSize: 36, fontWeight: 700, color: '#805ad5', margin: 0 }}>
                  {anomaly ? `${anomaly.anomaly_pct}` : '—'}
                </p>
                <p style={{ fontSize: 12, color: '#666', margin: '8px 0 0' }}>
                  {anomaly
                    ? (anomaly.is_anomalous ? `Unusual on ${anomaly.day}. ${anomaly.reason}` : anomaly.reason)
                    : 'Not enough logs to score this user.'}
                </p>
              </div>
            </div>

            <div style={{ background: 'white', borderRadius: 12, padding: 24, marginBottom: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 20px' }}>Violation Timeline</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={userData.timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#e53e3e" strokeWidth={2} dot={{ fill: '#e53e3e', r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>Violations — {selectedUser}</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                    {['Timestamp', 'GDPR Article', 'Reason', 'Risk Score', 'Severity', 'Status'].map(heading => (
                      <th key={heading} style={{
                        textAlign: 'left', padding: '8px 12px',
                        fontSize: 11, color: '#666', letterSpacing: 0.5, fontWeight: 600,
                      }}>
                        {heading.toUpperCase()}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {userData.violations.map(violation => (
                    <tr key={violation.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '12px 12px', color: '#444' }}>{violation.detected_at?.slice(0, 16) || '—'}</td>
                      <td style={{ padding: '12px 12px', fontWeight: 600 }}>{violation.rule.gdpr_article}</td>
                      <td style={{ padding: '12px 12px', color: '#555', maxWidth: 280 }}>{violation.reason}</td>
                      <td style={{ padding: '12px 12px', fontWeight: 600 }}>
                        {violation.is_anomaly ? `${Math.round(violation.risk_score * 100)}` : violation.risk_score}
                      </td>
                      <td style={{ padding: '12px 12px' }}>
                        <span style={{
                          fontSize: 11, padding: '3px 8px', borderRadius: 4,
                          background: `${severityColor[violation.rule.severity]}20`,
                          color: severityColor[violation.rule.severity],
                          fontWeight: 600,
                        }}>
                          {violation.rule.severity}
                        </span>
                      </td>
                      <td style={{ padding: '12px 12px' }}>
                        <span style={{
                          fontSize: 11, padding: '3px 8px', borderRadius: 4,
                          background: statusColor[violation.status]?.bg || '#f0f0f0',
                          color: statusColor[violation.status]?.text || '#666',
                          fontWeight: 600,
                        }}>
                          {violation.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {userData.violations.length === 0 && (
                <p style={{ textAlign: 'center', color: '#666', padding: 32 }}>
                  No violations found for this user.
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
