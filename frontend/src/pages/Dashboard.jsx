import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const API = 'http://127.0.0.1:8000/api'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [violations, setViolations] = useState([])
  const [simulating, setSimulating] = useState(false)
  const [simResult, setSimResult] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get(`${API}/stats/`).then(r => setStats(r.data))
    axios.get(`${API}/violations/`).then(r => setViolations(r.data.slice(0, 5)))
  }, [])

  function handleLogout() {
    localStorage.clear()
    navigate('/login')
  }

  async function handleSimulate() {
    setSimulating(true)
    setSimResult(null)
    try {
      const res = await axios.post(`${API}/simulate/`)
      setSimResult(res.data)
      axios.get(`${API}/stats/`).then(r => setStats(r.data))
      axios.get(`${API}/violations/`).then(r => setViolations(r.data.slice(0, 5)))
    } catch (e) {
      setSimResult({ message: 'Simulation failed' })
    }
    setSimulating(false)
  }

  const severityColor = { CRITICAL: '#e53e3e', HIGH: '#dd6b20', MEDIUM: '#d69e2e', LOW: '#38a169' }

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
            display: 'flex', alignItems: 'center', gap: 10, padding: '10px 24px',
            color: 'white', textDecoration: 'none', background: '#2d2d44', fontSize: 14
          }}>Dashboard</Link>
          <Link to="/violations" style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '10px 24px',
            color: '#8892b0', textDecoration: 'none', fontSize: 14
          }}>Violations</Link>
        </nav>
        <div style={{ padding: '16px 24px', borderTop: '1px solid #2d2d44' }}>
          <p style={{ fontSize: 13, fontWeight: 500 }}>Compliance Officer</p>
          <button onClick={handleLogout} style={{
            marginTop: 8, background: 'none', border: '1px solid #444',
            color: '#8892b0', padding: '4px 12px', borderRadius: 4,
            fontSize: 12, cursor: 'pointer'
          }}>Logout</button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>Dashboard Overview</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, color: '#666' }}>{new Date().toDateString()}</span>
            <button
              onClick={handleSimulate}
              disabled={simulating}
              style={{
                padding: '10px 20px',
                background: simulating ? '#999' : '#e53e3e',
                color: 'white', border: 'none', borderRadius: 8,
                fontSize: 13, fontWeight: 600,
                cursor: simulating ? 'not-allowed' : 'pointer'
              }}
            >
              {simulating ? 'Simulating...' : 'Simulate Employee Action'}
            </button>
          </div>
        </div>

        {/* Simulation Result Box */}
        {simResult && (
          <div style={{
            background: '#fff8e1', border: '1px solid #f6c90e',
            borderRadius: 10, padding: 16, marginBottom: 20
          }}>
            <p style={{ fontWeight: 600, marginBottom: 6 }}>Simulation Result</p>
            <p style={{ fontSize: 13, color: '#555', marginBottom: 4 }}>
              User: <strong>{simResult.user}</strong>
            </p>
            <p style={{ fontSize: 13, color: '#555', marginBottom: 4 }}>
              Action: <strong>{simResult.action}</strong>
            </p>
            <p style={{ fontSize: 13, color: '#555', marginBottom: 4 }}>
              Violations triggered: <strong style={{ color: '#e53e3e' }}>{simResult.violations_triggered}</strong>
            </p>
            {simResult.rules_fired && simResult.rules_fired.map(r => (
              <p key={r} style={{ fontSize: 12, color: '#888', marginLeft: 12 }}>• {r}</p>
            ))}
          </div>
        )}

        {/* Stat Cards */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
            {[
              { label: 'Total Violations', value: stats.total_violations, color: '#e53e3e' },
              { label: 'Anomalies Detected', value: stats.anomaly_count, color: '#dd6b20' },
              { label: 'Compliance Score', value: `${stats.compliance_score}%`, color: '#38a169' },
              { label: 'Logs Analyzed', value: stats.total_logs, color: '#3182ce' },
            ].map(card => (
              <div key={card.label} style={{
                background: 'white', borderRadius: 12, padding: 20,
                borderTop: `4px solid ${card.color}`
              }}>
                <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, marginBottom: 8 }}>
                  {card.label.toUpperCase()}
                </p>
                <p style={{ fontSize: 32, fontWeight: 700, color: card.color }}>{card.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Bottom Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

          {/* Bar Chart */}
          {stats && (
            <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 20 }}>
                Violations by GDPR Article
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={stats.by_article}>
                  <XAxis dataKey="rule__gdpr_article" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {stats.by_article.map((_, i) => (
                      <Cell key={i} fill={['#e53e3e', '#dd6b20', '#d69e2e', '#38a169', '#3182ce'][i % 5]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent Violations */}
          <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600 }}>Recent Violations</h3>
              <Link to="/violations" style={{ fontSize: 13, color: '#3182ce', textDecoration: 'none' }}>
                View all
              </Link>
            </div>
            {violations.map(v => (
              <div key={v.id} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 0', borderBottom: '1px solid #f0f0f0'
              }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500 }}>{v.log.user_id}</p>
                  <p style={{ fontSize: 11, color: '#666' }}>{v.rule.gdpr_article}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 4,
                    background: severityColor[v.rule.severity] + '20',
                    color: severityColor[v.rule.severity], fontWeight: 600
                  }}>{v.rule.severity}</span>
                  <p style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
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