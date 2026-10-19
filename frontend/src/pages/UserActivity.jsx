import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts'
import Sidebar from '../components/Sidebar'
import AlertBanner from '../components/AlertBanner'
import api from '../utils/axios'


const severityColor = {
  CRITICAL: '#e53e3e',
  HIGH: '#dd6b20',
  MEDIUM: '#d69e2e',
  LOW: '#38a169'
}

const statusColor = {
  OPEN: { bg: '#fff0f0', text: '#e53e3e' },
  REVIEWING: { bg: '#fff8e1', text: '#dd6b20' },
  RESOLVED: { bg: '#f0fff4', text: '#38a169' }
}

export default function UserActivity() {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [userData, setUserData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.get(`/violations/`)
      .then(r => {
        const uniqueUsers = [...new Set(r.data.map(v => v.log.user_id))]
        setUsers(uniqueUsers)
        if (uniqueUsers.length > 0) setSelectedUser(uniqueUsers[0])
      })
      .catch(() => {
        const mock = ['u_hassan', 'u_ayesha', 'u_tariq', 'u_zara', 'u_bilal']
        setUsers(mock)
        setSelectedUser(mock[0])
      })
  }, [])

  useEffect(() => {
    if (!selectedUser) return
    setLoading(true)
    api.get(`/violations/`)
      .then(r => {
        const all = r.data
        const userViolations = all.filter(v => v.log.user_id === selectedUser)
        const avgRisk = userViolations.length > 0
          ? (userViolations.reduce((s, v) => s + v.risk_score, 0) / userViolations.length).toFixed(2)
          : 0
        const articleCounts = {}
        userViolations.forEach(v => {
          const a = v.rule.gdpr_article
          articleCounts[a] = (articleCounts[a] || 0) + 1
        })
        const mostCommon = Object.keys(articleCounts).length > 0
          ? Object.entries(articleCounts).sort((a, b) => b[1] - a[1])[0][0]
          : 'N/A'
        setUserData({
          total_violations: userViolations.length,
          avg_risk_score: avgRisk,
          most_common: mostCommon,
          violations: userViolations,
          timeline: buildTimeline(userViolations)
        })
        setLoading(false)
      })
      .catch(() => {
        setUserData(getMockData(selectedUser))
        setLoading(false)
      })
  }, [selectedUser])

  function buildTimeline(violations) {
    const counts = {}
    violations.forEach(v => {
      const date = v.detected_at?.slice(0, 10) || 'Unknown'
      counts[date] = (counts[date] || 0) + 1
    })
    return Object.entries(counts)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, count]) => ({ date, count }))
  }

  function getMockData(user) {
    return {
      total_violations: 7,
      avg_risk_score: '0.72',
      most_common: 'Art. 32',
      violations: [
        { id: 1, detected_at: '2025-06-12 09:42', log: { user_id: user }, rule: { gdpr_article: 'Art. 5', severity: 'CRITICAL' }, risk_score: 0.92, reason: 'Bulk export of personal records', status: 'OPEN' },
        { id: 2, detected_at: '2025-06-11 14:30', log: { user_id: user }, rule: { gdpr_article: 'Art. 32', severity: 'HIGH' }, risk_score: 0.78, reason: 'After-hours sensitive data access', status: 'REVIEWING' },
        { id: 3, detected_at: '2025-06-10 11:15', log: { user_id: user }, rule: { gdpr_article: 'Art. 6', severity: 'MEDIUM' }, risk_score: 0.54, reason: 'Missing lawful basis declaration', status: 'RESOLVED' },
        { id: 4, detected_at: '2025-06-09 16:20', log: { user_id: user }, rule: { gdpr_article: 'Art. 25', severity: 'HIGH' }, risk_score: 0.71, reason: 'Excess data access beyond role scope', status: 'OPEN' },
      ],
      timeline: [
        { date: 'Jun 8', count: 1 },
        { date: 'Jun 9', count: 2 },
        { date: 'Jun 10', count: 1 },
        { date: 'Jun 11', count: 2 },
        { date: 'Jun 12', count: 1 },
      ]
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <AlertBanner />
      <Sidebar role="compliance" />

      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 28
        }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>User Activity</h1>
          <select
            value={selectedUser}
            onChange={e => setSelectedUser(e.target.value)}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: '1px solid #ddd',
              fontSize: 14,
              background: 'white',
              cursor: 'pointer',
              minWidth: 180
            }}
          >
            {users.map(u => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
              <button
      onClick={() => window.open(
        `http://127.0.0.1:8000/api/user-pdf/${encodeURIComponent(selectedUser)}/`,
        '_blank'
      )}
      disabled={!selectedUser}
      style={{
        padding: '8px 18px',
        background: selectedUser ? '#1a1a2e' : '#ccc',
        color: 'white',
        border: 'none',
        borderRadius: 8,
        fontSize: 13,
        fontWeight: 600,
        cursor: selectedUser ? 'pointer' : 'not-allowed'
      }}
    >
      Download Report
    </button>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: 60, color: '#666' }}>
            Loading user data...
          </div>
        )}

        {!loading && userData && (
          <>
            {/* Stat Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 16,
              marginBottom: 24
            }}>
              <div style={{
                background: 'white', borderRadius: 12,
                padding: 20, borderTop: '4px solid #e53e3e'
              }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>
                  TOTAL VIOLATIONS
                </p>
                <p style={{ fontSize: 36, fontWeight: 700, color: '#e53e3e', margin: 0 }}>
                  {userData.total_violations}
                </p>
              </div>
              <div style={{
                background: 'white', borderRadius: 12,
                padding: 20, borderTop: '4px solid #dd6b20'
              }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>
                  AVG RISK SCORE
                </p>
                <p style={{ fontSize: 36, fontWeight: 700, color: '#dd6b20', margin: 0 }}>
                  {userData.avg_risk_score}
                </p>
              </div>
              <div style={{
                background: 'white', borderRadius: 12,
                padding: 20, borderTop: '4px solid #3182ce'
              }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>
                  MOST COMMON VIOLATION
                </p>
                <p style={{ fontSize: 28, fontWeight: 700, color: '#3182ce', margin: 0 }}>
                  {userData.most_common}
                </p>
              </div>
            </div>

            {/* Timeline Chart */}
            <div style={{
              background: 'white', borderRadius: 12,
              padding: 24, marginBottom: 24
            }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 20px' }}>
                Violation Timeline
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={userData.timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#e53e3e"
                    strokeWidth={2}
                    dot={{ fill: '#e53e3e', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Violations Table */}
            <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>
                Violations — {selectedUser}
              </h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                    {['Timestamp', 'GDPR Article', 'Reason', 'Risk Score', 'Severity', 'Status'].map(h => (
                      <th key={h} style={{
                        textAlign: 'left', padding: '8px 12px',
                        fontSize: 11, color: '#666',
                        letterSpacing: 0.5, fontWeight: 600
                      }}>
                        {h.toUpperCase()}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {userData.violations.map(v => (
                    <tr key={v.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '12px 12px', color: '#444' }}>
                        {v.detected_at?.slice(0, 16) || '—'}
                      </td>
                      <td style={{ padding: '12px 12px', fontWeight: 600 }}>
                        {v.rule.gdpr_article}
                      </td>
                      <td style={{ padding: '12px 12px', color: '#555', maxWidth: 200 }}>
                        {v.reason}
                      </td>
                      <td style={{ padding: '12px 12px', fontWeight: 600 }}>
                        {v.risk_score}
                      </td>
                      <td style={{ padding: '12px 12px' }}>
                        <span style={{
                          fontSize: 11, padding: '3px 8px', borderRadius: 4,
                          background: severityColor[v.rule.severity] + '20',
                          color: severityColor[v.rule.severity],
                          fontWeight: 600
                        }}>
                          {v.rule.severity}
                        </span>
                      </td>
                      <td style={{ padding: '12px 12px' }}>
                        <span style={{
                          fontSize: 11, padding: '3px 8px', borderRadius: 4,
                          background: statusColor[v.status]?.bg || '#f0f0f0',
                          color: statusColor[v.status]?.text || '#666',
                          fontWeight: 600
                        }}>
                          {v.status}
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