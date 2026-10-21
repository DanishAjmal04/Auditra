import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import Sidebar from '../components/Sidebar'
import AlertBanner from '../components/AlertBanner'
import api from '../utils/axios'


export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [violations, setViolations] = useState([])
  const [logs, setLogs] = useState([])
  const [checkedAt, setCheckedAt] = useState(null)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  function fetchData() {
    api.get('/stats/').then(r => setStats(r.data)).catch(() => setStats(null))
    api.get('/violations/').then(r => setViolations(r.data.slice(0, 5))).catch(() => setViolations([]))
    api.get('/logs/').then(r => setLogs(r.data.slice(0, 6))).catch(() => setLogs([]))
    setCheckedAt(new Date())
  }

  const severityColor = {
    CRITICAL: '#e53e3e',
    HIGH: '#dd6b20',
    MEDIUM: '#d69e2e',
    LOW: '#38a169'
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
       
      {/* Sidebar */}
      <Sidebar role="compliance" />

      {/* Main Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 28
        }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Dashboard Overview</h1>
          <span style={{ fontSize: 13, color: '#666' }}>
            Live · checked {checkedAt ? checkedAt.toLocaleTimeString() : '…'}
          </span>
        </div>

        {/* Stat Cards */}
        {stats && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 16,
            marginBottom: 28
          }}>
            {[
              { label: 'Total Violations', value: stats.total_violations, color: '#e53e3e' },
              { label: 'Anomalies Detected', value: stats.anomaly_count, color: '#dd6b20' },
              { label: 'Compliance Score', value: `${stats.compliance_score}%`, color: '#38a169' },
              { label: 'Logs Analyzed', value: stats.total_logs, color: '#3182ce' },
            ].map(card => (
              <div key={card.label} style={{
                background: 'white',
                borderRadius: 12,
                padding: 20,
                borderTop: `4px solid ${card.color}`
              }}>
                <p style={{
                  fontSize: 11,
                  color: '#666',
                  letterSpacing: 1,
                  marginBottom: 8,
                  margin: '0 0 8px'
                }}>
                  {card.label.toUpperCase()}
                </p>
                <p style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: card.color,
                  margin: 0
                }}>
                  {card.value}
                </p>
              </div>
            ))}
          </div>
        )}

        <div style={{ background: 'white', borderRadius: 12, padding: 24, marginBottom: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px' }}>
            Latest activity received
          </h3>
          {logs.length === 0 && (
            <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
              No activity yet. When this laptop sends a Windows event, it appears here.
            </p>
          )}
          {logs.map(log => (
            <div key={log.id} style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 12,
              padding: '8px 0',
              borderBottom: '1px solid #f0f0f0',
              fontSize: 13
            }}>
              <span style={{ fontWeight: 600 }}>{log.user_id}</span>
              <span>{log.action}</span>
              <span style={{ color: '#555' }}>{log.resource_accessed}</span>
              <span style={{ color: '#888' }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>

        {/* Bottom Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

          {/* Bar Chart */}
          {stats && (
            <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 20, margin: '0 0 20px' }}>
                Violations by GDPR Article
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={stats.by_article}>
                  <XAxis dataKey="rule__gdpr_article" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {stats.by_article.map((_, i) => (
                      <Cell
                        key={i}
                        fill={['#e53e3e','#dd6b20','#d69e2e','#38a169','#3182ce'][i % 5]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent Violations */}
          <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 16
            }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
                Recent Violations
              </h3>
              <Link to="/violations" style={{
                fontSize: 13,
                color: '#3182ce',
                textDecoration: 'none'
              }}>
                View all
              </Link>
            </div>
            {violations.map(v => (
              <div key={v.id} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 0',
                borderBottom: '1px solid #f0f0f0'
              }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500, margin: 0 }}>
                    {v.log.user_id}
                  </p>
                  <p style={{ fontSize: 11, color: '#666', margin: '2px 0 0' }}>
                    {v.rule.gdpr_article}
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: 11,
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: severityColor[v.rule.severity] + '20',
                    color: severityColor[v.rule.severity],
                    fontWeight: 600
                  }}>
                    {v.rule.severity}
                  </span>
                  <p style={{ fontSize: 11, color: '#666', margin: '2px 0 0' }}>
                    Score: {v.risk_score}
                  </p>
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  )
}