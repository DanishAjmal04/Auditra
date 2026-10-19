import { useState, useEffect } from 'react'
import api from '../utils/axios'


export default function AlertBanner() {
  const [alerts, setAlerts] = useState([])
  const [dismissed, setDismissed] = useState([])

  useEffect(() => {
    checkAlerts()
    const interval = setInterval(checkAlerts, 30000)
    return () => clearInterval(interval)
  }, [])

  async function checkAlerts() {
    try {
      const res = await api.get(`/violations/?severity=CRITICAL&status=OPEN`)
      const critical = res.data
        .filter(v => v.rule?.severity === 'CRITICAL' && v.status === 'OPEN')
        .slice(0, 3)
      setAlerts(critical)
    } catch {
      // silent fail — no mock alerts on load
    }
  }

  function dismiss(id) {
    setDismissed(prev => [...prev, id])
  }

  const visible = alerts.filter(a => !dismissed.includes(a.id))

  if (visible.length === 0) return null

  return (
    <div style={{
      position: 'fixed',
      top: 16,
      right: 16,
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      maxWidth: 400
    }}>
      {visible.map(alert => (
        <div
          key={alert.id}
          style={{
            background: '#1a1a2e',
            border: '1px solid #e53e3e',
            borderLeft: '4px solid #e53e3e',
            borderRadius: 10,
            padding: '14px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            boxShadow: '0 4px 20px rgba(229,62,62,0.2)',
            animation: 'slideIn 0.3s ease'
          }}
        >
          {/* Top Row */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                fontSize: 11, padding: '2px 8px',
                borderRadius: 4, background: '#e53e3e',
                color: 'white', fontWeight: 700,
                letterSpacing: 0.5
              }}>
                🚨 CRITICAL
              </span>
              <span style={{ fontSize: 12, color: '#a8b2d8', fontWeight: 600 }}>
                {alert.rule?.gdpr_article}
              </span>
            </div>
            <button
              onClick={() => dismiss(alert.id)}
              style={{
                background: 'none', border: 'none',
                color: '#8892b0', fontSize: 18,
                cursor: 'pointer', lineHeight: 1,
                padding: '0 4px'
              }}
            >
              ×
            </button>
          </div>

          {/* User + Reason */}
          <div>
            <p style={{ margin: 0, fontSize: 13, color: 'white', fontWeight: 600 }}>
              {alert.log?.user_id}
            </p>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: '#8892b0' }}>
              {alert.reason}
            </p>
          </div>

          {/* Bottom Row */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 4
          }}>
            <span style={{ fontSize: 11, color: '#8892b0' }}>
              Risk Score: <strong style={{ color: '#e53e3e' }}>{alert.risk_score}</strong>
            </span>
            <span style={{ fontSize: 11, color: '#8892b0' }}>
              {alert.detected_at?.slice(0, 16)}
            </span>
          </div>
        </div>
      ))}

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(40px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  )
}