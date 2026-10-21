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
  const newest = visible[0]

  if (!newest) return null

  return (
    <div style={{
      position: 'fixed',
      top: 16,
      right: 16,
      zIndex: 1000,
      maxWidth: 360
    }}>
      <div
        style={{
          background: '#1a1a2e',
          border: '1px solid #e53e3e',
          borderLeft: '4px solid #e53e3e',
          borderRadius: 10,
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 6
        }}
      >
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
              CRITICAL
            </span>
            <span style={{ fontSize: 12, color: '#a8b2d8', fontWeight: 600 }}>
              {visible.length} open
            </span>
          </div>
          <button
            onClick={() => dismiss(newest.id)}
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
        <div>
          <p style={{ margin: 0, fontSize: 13, color: 'white', fontWeight: 600 }}>
            {newest.rule?.gdpr_article} · {newest.log?.user_id}
          </p>
          <p style={{ margin: '2px 0 0', fontSize: 12, color: '#8892b0' }}>
            {newest.reason}
          </p>
        </div>
        <span style={{ fontSize: 11, color: '#8892b0' }}>
          Risk score {newest.risk_score}. Open Violations to review the rest.
        </span>
      </div>
    </div>
  )
}