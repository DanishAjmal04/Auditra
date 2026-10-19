import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import Sidebar from '../components/Sidebar'
import AlertBanner from '../components/AlertBanner'
import api from '../utils/axios'


export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [violations, setViolations] = useState([])
  const [simulating, setSimulating] = useState(false)
  const [simResult, setSimResult] = useState(null)

  useEffect(() => {
  fetchData()
  
  // Har 30 seconds mein auto refresh
  const interval = setInterval(() => {
    fetchData()
  }, 30000)
  
  return () => clearInterval(interval)
}, [])

function fetchData() {
  api.get('/stats/').then(r => setStats(r.data))
  api.get('/violations/').then(r => setViolations(r.data.slice(0, 5)))
}

  async function handleSimulate() {
    setSimulating(true)
    setSimResult(null)
    try {
      const res = await api.post(`/simulate/`)
      setSimResult(res.data)
      fetchData()
    } catch (e) {
      setSimResult({ message: 'Simulation failed' })
    }
    setSimulating(false)
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, color: '#666' }}>
              {new Date().toDateString()}
            </span>
            <button
              onClick={handleSimulate}
              disabled={simulating}
              style={{
                padding: '10px 20px',
                background: simulating ? '#999' : '#e53e3e',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                cursor: simulating ? 'not-allowed' : 'pointer'
              }}
            >
              {simulating ? 'Simulating...' : 'Simulate Employee Action'}
            </button>
          </div>
        </div>

        {/* Simulation Result */}
        {simResult && (
          <div style={{
            background: '#fff8e1',
            border: '1px solid #f6c90e',
            borderRadius: 10,
            padding: 16,
            marginBottom: 20
          }}>
            <p style={{ fontWeight: 600, marginBottom: 6, margin: '0 0 6px' }}>
              Simulation Result
            </p>
            <p style={{ fontSize: 13, color: '#555', margin: '0 0 4px' }}>
              User: <strong>{simResult.user}</strong>
            </p>
            <p style={{ fontSize: 13, color: '#555', margin: '0 0 4px' }}>
              Action: <strong>{simResult.action}</strong>
            </p>
            <p style={{ fontSize: 13, color: '#555', margin: '0 0 4px' }}>
              Violations triggered:{' '}
              <strong style={{ color: '#e53e3e' }}>
                {simResult.violations_triggered}
              </strong>
            </p>
            {simResult.rules_fired && simResult.rules_fired.map(r => (
              <p key={r} style={{ fontSize: 12, color: '#888', margin: '2px 0 0 12px' }}>
                • {r}
              </p>
            ))}
          </div>
        )}

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