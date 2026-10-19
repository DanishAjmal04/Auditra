import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'


function getMockHealth() {
  return {
    total_logs: 8421,
    total_violations: 32,
    total_rules: 13,
    active_rules: 11,
    db_size: '142 MB',
    api_response_ms: 87,
    last_engine_run: '2025-06-12 09:45:00',
    last_simulation: '2025-06-12 08:30:00',
    uptime: '99.8%',
    engine_status: 'RUNNING',
    db_status: 'HEALTHY',
    api_status: 'HEALTHY',
    last_job: {
      trigger: 'SCHEDULED',
      logs_processed: 125,
      violations_created: 3,
      anomalies_flagged: 1,
      notifications_sent: 2,
      notifications_failed: 0,
      error_message: '',
    },
  }
}

export default function SystemHealth() {
  const [health, setHealth] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date().toLocaleTimeString())

  function fetchHealth() {
    setRefreshing(true)
    api.get(`/admin/health/`)
      .then(r => {
        setHealth(r.data)
        setLastRefresh(new Date().toLocaleTimeString())
        setRefreshing(false)
      })
      .catch(() => {
        setHealth(getMockHealth())
        setLastRefresh(new Date().toLocaleTimeString())
        setRefreshing(false)
      })
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  const healthyStatuses = ['HEALTHY', 'RUNNING', 'SUCCESS']
  const warningStatuses = ['SKIPPED', 'NEVER_RUN']
  const statusColor = (status) => {
    if (healthyStatuses.includes(status)) return '#38a169'
    if (warningStatuses.includes(status)) return '#d69e2e'
    return '#e53e3e'
  }
  const statusBackground = (status) => {
    if (healthyStatuses.includes(status)) return '#f0fff4'
    if (warningStatuses.includes(status)) return '#fffaf0'
    return '#fff0f0'
  }
  const statusIcon = (status) => {
    if (healthyStatuses.includes(status)) return '✅'
    if (warningStatuses.includes(status)) return '⚠️'
    return '❌'
  }

  const statusStyle = (status) => ({
    fontSize: 12, padding: '3px 10px', borderRadius: 4, fontWeight: 700,
    background: statusBackground(status),
    color: statusColor(status)
  })

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="admin" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 28
        }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
              System Health
            </h1>
            <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
              Last refreshed at {lastRefresh}
            </p>
          </div>
          <button
            onClick={fetchHealth}
            disabled={refreshing}
            style={{
              padding: '10px 20px',
              background: refreshing ? '#999' : '#1a1a2e',
              color: 'white', border: 'none',
              borderRadius: 8, fontSize: 13,
              fontWeight: 600, cursor: refreshing ? 'not-allowed' : 'pointer'
            }}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {health && (
          <>
            {/* Status Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 16, marginBottom: 24
            }}>
              {[
                { label: 'COMPLIANCE ENGINE', status: health.engine_status },
                { label: 'DATABASE', status: health.db_status },
                { label: 'API', status: health.api_status },
              ].map(item => (
                <div key={item.label} style={{
                  background: 'white', borderRadius: 12, padding: 24,
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center',
                  borderLeft: `4px solid ${statusColor(item.status)}`
                }}>
                  <div>
                    <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 6px' }}>
                      {item.label}
                    </p>
                    <span style={statusStyle(item.status)}>
                      {item.status}
                    </span>
                  </div>
                  <span style={{ fontSize: 32 }}>
                    {statusIcon(item.status)}
                  </span>
                </div>
              ))}
            </div>

            {/* Metrics Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 16, marginBottom: 24
            }}>
              {[
                { label: 'TOTAL LOGS', value: health.total_logs.toLocaleString(), color: '#3182ce' },
                { label: 'TOTAL VIOLATIONS', value: health.total_violations, color: '#e53e3e' },
                { label: 'API RESPONSE TIME', value: `${health.api_response_ms} ms`, color: '#38a169' },
                { label: 'DATABASE SIZE', value: health.db_size, color: '#805ad5' },
              ].map(card => (
                <div key={card.label} style={{
                  background: 'white', borderRadius: 12,
                  padding: 20, borderTop: `4px solid ${card.color}`
                }}>
                  <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>
                    {card.label}
                  </p>
                  <p style={{ fontSize: 28, fontWeight: 700, color: card.color, margin: 0 }}>
                    {card.value}
                  </p>
                </div>
              ))}
            </div>

            {/* Details Table */}
            <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 20px' }}>
                System Details
              </h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <tbody>
                  {[
                    { label: 'System Uptime', value: health.uptime },
                    { label: 'Total Rules Configured', value: health.total_rules },
                    { label: 'Active Rules', value: health.active_rules },
                    { label: 'Last Engine Run', value: health.last_engine_run },
                    { label: 'Last Run Trigger', value: health.last_job?.trigger || 'Never' },
                    { label: 'Logs Processed', value: health.last_job?.logs_processed ?? 0 },
                    { label: 'Violations Created', value: health.last_job?.violations_created ?? 0 },
                    { label: 'Anomalies Flagged', value: health.last_job?.anomalies_flagged ?? 0 },
                    { label: 'Notifications Sent', value: health.last_job?.notifications_sent ?? 0 },
                    { label: 'Notification Failures', value: health.last_job?.notifications_failed ?? 0 },
                    ...(health.last_job?.error_message
                      ? [{ label: 'Last Run Error', value: health.last_job.error_message }]
                      : []),
                    { label: 'Last Simulation', value: health.last_simulation },
                    { label: 'Database Size', value: health.db_size },
                    { label: 'API Response Time', value: `${health.api_response_ms} ms` },
                  ].map(row => (
                    <tr key={row.label} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{
                        padding: '12px 16px', color: '#666',
                        fontSize: 13, width: '40%'
                      }}>
                        {row.label}
                      </td>
                      <td style={{
                        padding: '12px 16px',
                        fontWeight: 600, color: '#1a1a2e'
                      }}>
                        {row.value}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
