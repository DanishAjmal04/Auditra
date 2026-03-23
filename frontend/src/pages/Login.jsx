import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  function handleLogin(e) {
    e.preventDefault()
    if (email === 'compliance@auditra.com' && password === 'Auditra@2026') {
      localStorage.setItem('auditra_auth', 'true')
      localStorage.setItem('auditra_user', 'Compliance Officer')
      navigate('/dashboard')
    } else {
      setError('Invalid email or password')
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      {/* Left Panel */}
      <div style={{
        width: '40%', background: '#1a1a2e', color: 'white',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '60px 50px'
      }}>
        <h1 style={{ fontSize: 32, fontWeight: 700, marginBottom: 8 }}>Auditra</h1>
        <p style={{ color: '#8892b0', fontSize: 13, letterSpacing: 2, marginBottom: 40 }}>
          GDPR COMPLIANCE MONITOR
        </p>
        <h2 style={{ fontSize: 22, fontWeight: 600, marginBottom: 16, lineHeight: 1.4 }}>
          Automated compliance monitoring for your organization
        </h2>
        <p style={{ color: '#8892b0', fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
          Auditra continuously analyzes system access logs, detects GDPR violations,
          and generates audit-ready compliance reports.
        </p>
        {['Rule-based violation detection', 'AI-assisted anomaly detection',
          'Automated compliance reporting', 'GDPR Article traceability'].map(f => (
          <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4fc3f7' }} />
            <span style={{ color: '#ccd6f6', fontSize: 14 }}>{f}</span>
          </div>
        ))}
      </div>

      {/* Right Panel */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: 'white'
      }}>
        <div style={{ width: 400 }}>
          <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Welcome back</h2>
          <p style={{ color: '#666', marginBottom: 32 }}>Sign in to your Auditra account</p>

          {error && (
            <div style={{
              background: '#fff0f0', border: '1px solid #ffcccc',
              color: '#cc0000', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 14
            }}>{error}</div>
          )}

          <form onSubmit={handleLogin}>
            <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 6 }}>
              Email Address
            </label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="compliance@auditra.com" required
              style={{
                width: '100%', padding: '12px 14px', border: '1px solid #ddd',
                borderRadius: 8, fontSize: 14, marginBottom: 16, outline: 'none'
              }}
            />
            <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 6 }}>
              Password
            </label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required
              style={{
                width: '100%', padding: '12px 14px', border: '1px solid #ddd',
                borderRadius: 8, fontSize: 14, marginBottom: 24, outline: 'none'
              }}
            />
            <button type="submit" style={{
              width: '100%', padding: '13px', background: '#1a1a2e',
              color: 'white', border: 'none', borderRadius: 8,
              fontSize: 15, fontWeight: 600, cursor: 'pointer'
            }}>
              Sign In
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#666' }}>
            Demo credentials: compliance@auditra.com / admin123
          </p>
        </div>
      </div>
    </div>
  )
}