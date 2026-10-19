import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'


function getMockLogs() {
  return [
    { id: 1, user_id: 'u_hassan', action: 'EXPORT', resource_accessed: 'patient_records', resource_sensitivity: 'HIGH', ip_address: '192.168.1.10', timestamp: '2025-06-12 09:42:00', purpose: 'Research' },
    { id: 2, user_id: 'u_ayesha', action: 'READ', resource_accessed: 'financial_reports', resource_sensitivity: 'HIGH', ip_address: '192.168.1.22', timestamp: '2025-06-12 02:17:00', purpose: null },
    { id: 3, user_id: 'u_tariq', action: 'DELETE', resource_accessed: 'user_profiles', resource_sensitivity: 'MEDIUM', ip_address: '192.168.1.35', timestamp: '2025-06-11 14:30:00', purpose: 'Cleanup' },
    { id: 4, user_id: 'u_zara', action: 'READ', resource_accessed: 'biometric_data', resource_sensitivity: 'HIGH', ip_address: '192.168.1.41', timestamp: '2025-06-11 11:15:00', purpose: null },
    { id: 5, user_id: 'u_bilal', action: 'WRITE', resource_accessed: 'employee_records', resource_sensitivity: 'MEDIUM', ip_address: '192.168.1.18', timestamp: '2025-06-10 16:20:00', purpose: 'Update' },
    { id: 6, user_id: 'u_nadia', action: 'EXPORT', resource_accessed: 'customer_data', resource_sensitivity: 'HIGH', ip_address: '192.168.1.55', timestamp: '2025-06-10 09:00:00', purpose: 'Audit' },
    { id: 7, user_id: 'u_omar', action: 'READ', resource_accessed: 'health_records', resource_sensitivity: 'HIGH', ip_address: '192.168.1.62', timestamp: '2025-06-09 22:45:00', purpose: null },
    { id: 8, user_id: 'u_hassan', action: 'DELETE', resource_accessed: 'payment_data', resource_sensitivity: 'HIGH', ip_address: '192.168.1.10', timestamp: '2025-06-09 10:30:00', purpose: 'GDPR Request' },
    { id: 9, user_id: 'u_sara', action: 'READ', resource_accessed: 'audit_logs', resource_sensitivity: 'LOW', ip_address: '192.168.1.77', timestamp: '2025-06-08 14:00:00', purpose: 'Compliance' },
    { id: 10, user_id: 'u_tariq', action: 'WRITE', resource_accessed: 'criminal_records', resource_sensitivity: 'HIGH', ip_address: '192.168.1.35', timestamp: '2025-06-08 08:15:00', purpose: null },
  ]
}

const sensitivityColor = {
  HIGH: { bg: '#fff0f0', text: '#e53e3e' },
  MEDIUM: { bg: '#fff8e1', text: '#dd6b20' },
  LOW: { bg: '#f0fff4', text: '#38a169' }
}

const actionColor = {
  EXPORT: { bg: '#fff0f0', text: '#e53e3e' },
  DELETE: { bg: '#fff0f0', text: '#e53e3e' },
  WRITE: { bg: '#fff8e1', text: '#dd6b20' },
  READ: { bg: '#f0f4ff', text: '#3182ce' }
}

export default function ViewLogs() {
  const [logs, setLogs] = useState([])
  const [filters, setFilters] = useState({
    user: '',
    action: '',
    sensitivity: '',
    dateFrom: '',
    dateTo: ''
  })
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    api.get(`/logs/`)
      .then(r => setLogs(r.data))
      .catch(() => setLogs(getMockLogs()))
  }, [])

  const filtered = logs.filter(log => {
    if (filters.user && !log.user_id.toLowerCase().includes(filters.user.toLowerCase())) return false
    if (filters.action && log.action !== filters.action) return false
    if (filters.sensitivity && log.resource_sensitivity !== filters.sensitivity) return false
    if (filters.dateFrom && log.timestamp.slice(0, 10) < filters.dateFrom) return false
    if (filters.dateTo && log.timestamp.slice(0, 10) > filters.dateTo) return false
    return true
  })

  function clearFilters() {
    setFilters({ user: '', action: '', sensitivity: '', dateFrom: '', dateTo: '' })
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="admin" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
            View All Logs
          </h1>
          <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
            {filtered.length} of {logs.length} logs shown.
          </p>
        </div>

        {/* Filters */}
        <div style={{
          background: 'white', borderRadius: 12,
          padding: 20, marginBottom: 20
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: 12, marginBottom: 12
          }}>
            <div>
              <label style={{
                fontSize: 11, fontWeight: 600,
                color: '#666', display: 'block', marginBottom: 6
              }}>
                USER
              </label>
              <input
                value={filters.user}
                onChange={e => setFilters({ ...filters, user: e.target.value })}
                placeholder="Search user..."
                style={{
                  width: '100%', padding: '8px 10px',
                  border: '1px solid #ddd', borderRadius: 6,
                  fontSize: 12, outline: 'none', boxSizing: 'border-box'
                }}
              />
            </div>
            <div>
              <label style={{
                fontSize: 11, fontWeight: 600,
                color: '#666', display: 'block', marginBottom: 6
              }}>
                ACTION
              </label>
              <select
                value={filters.action}
                onChange={e => setFilters({ ...filters, action: e.target.value })}
                style={{
                  width: '100%', padding: '8px 10px',
                  border: '1px solid #ddd', borderRadius: 6,
                  fontSize: 12, outline: 'none',
                  background: 'white', boxSizing: 'border-box'
                }}
              >
                <option value="">All Actions</option>
                <option>READ</option>
                <option>WRITE</option>
                <option>DELETE</option>
                <option>EXPORT</option>
              </select>
            </div>
            <div>
              <label style={{
                fontSize: 11, fontWeight: 600,
                color: '#666', display: 'block', marginBottom: 6
              }}>
                SENSITIVITY
              </label>
              <select
                value={filters.sensitivity}
                onChange={e => setFilters({ ...filters, sensitivity: e.target.value })}
                style={{
                  width: '100%', padding: '8px 10px',
                  border: '1px solid #ddd', borderRadius: 6,
                  fontSize: 12, outline: 'none',
                  background: 'white', boxSizing: 'border-box'
                }}
              >
                <option value="">All Levels</option>
                <option>HIGH</option>
                <option>MEDIUM</option>
                <option>LOW</option>
              </select>
            </div>
            <div>
              <label style={{
                fontSize: 11, fontWeight: 600,
                color: '#666', display: 'block', marginBottom: 6
              }}>
                FROM DATE
              </label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={e => setFilters({ ...filters, dateFrom: e.target.value })}
                style={{
                  width: '100%', padding: '8px 10px',
                  border: '1px solid #ddd', borderRadius: 6,
                  fontSize: 12, outline: 'none', boxSizing: 'border-box'
                }}
              />
            </div>
            <div>
              <label style={{
                fontSize: 11, fontWeight: 600,
                color: '#666', display: 'block', marginBottom: 6
              }}>
                TO DATE
              </label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={e => setFilters({ ...filters, dateTo: e.target.value })}
                style={{
                  width: '100%', padding: '8px 10px',
                  border: '1px solid #ddd', borderRadius: 6,
                  fontSize: 12, outline: 'none', boxSizing: 'border-box'
                }}
              />
            </div>
          </div>
          <button
            onClick={clearFilters}
            style={{
              padding: '6px 16px',
              background: '#f0f0f0',
              color: '#555', border: 'none',
              borderRadius: 6, fontSize: 12,
              cursor: 'pointer', fontWeight: 600
            }}
          >
            Clear Filters
          </button>
        </div>

        {/* Logs Table */}
        <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                {['Timestamp', 'User', 'Action', 'Resource', 'Sensitivity', 'IP Address', 'Details'].map(h => (
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
              {filtered.map(log => (
                <>
                  <tr
                    key={log.id}
                    style={{
                      borderBottom: expanded === log.id ? 'none' : '1px solid #f0f0f0',
                      background: expanded === log.id ? '#f8f9ff' : 'white',
                      cursor: 'pointer'
                    }}
                    onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                  >
                    <td style={{ padding: '11px 12px', color: '#444', fontSize: 12 }}>
                      {log.timestamp}
                    </td>
                    <td style={{ padding: '11px 12px', fontWeight: 600 }}>
                      {log.user_id}
                    </td>
                    <td style={{ padding: '11px 12px' }}>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 4,
                        background: actionColor[log.action]?.bg || '#f0f0f0',
                        color: actionColor[log.action]?.text || '#666',
                        fontWeight: 600
                      }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ padding: '11px 12px', color: '#555' }}>
                      {log.resource_accessed}
                    </td>
                    <td style={{ padding: '11px 12px' }}>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 4,
                        background: sensitivityColor[log.resource_sensitivity]?.bg,
                        color: sensitivityColor[log.resource_sensitivity]?.text,
                        fontWeight: 600
                      }}>
                        {log.resource_sensitivity}
                      </span>
                    </td>
                    <td style={{ padding: '11px 12px', color: '#555', fontSize: 12 }}>
                      {log.ip_address}
                    </td>
                    <td style={{ padding: '11px 12px', color: log.purpose ? '#555' : '#bbb', fontSize: 12 }}>
                      {log.purpose || 'Not declared'}
                    </td>
                    <td style={{ padding: '11px 12px' }}>
                      <span style={{ fontSize: 18, color: '#888' }}>
                        {expanded === log.id ? '▲' : '▼'}
                      </span>
                    </td>
                  </tr>

                  {/* Expanded Row */}
                  {expanded === log.id && (
                    <tr key={`exp-${log.id}`}>
                      <td colSpan={8} style={{
                        padding: '0 12px 16px',
                        background: '#f8f9ff',
                        borderBottom: '1px solid #f0f0f0'
                      }}>
                        <div style={{
                          background: '#1a1a2e',
                          borderRadius: 8, padding: 16,
                          fontFamily: 'monospace', fontSize: 12,
                          color: '#a8b2d8', lineHeight: 1.8
                        }}>
                          <span style={{ color: '#4fc3f7' }}>LOG ID:</span> {log.id}{' '}
                          &nbsp;&nbsp;
                          <span style={{ color: '#4fc3f7' }}>USER:</span> {log.user_id}{' '}
                          &nbsp;&nbsp;
                          <span style={{ color: '#4fc3f7' }}>ACTION:</span> {log.action}{' '}
                          <br />
                          <span style={{ color: '#4fc3f7' }}>RESOURCE:</span> {log.resource_accessed}{' '}
                          &nbsp;&nbsp;
                          <span style={{ color: '#4fc3f7' }}>SENSITIVITY:</span> {log.resource_sensitivity}{' '}
                          &nbsp;&nbsp;
                          <span style={{ color: '#4fc3f7' }}>IP:</span> {log.ip_address}
                          <br />
                          <span style={{ color: '#4fc3f7' }}>TIMESTAMP:</span> {log.timestamp}{' '}
                          &nbsp;&nbsp;
                          <span style={{ color: '#4fc3f7' }}>PURPOSE:</span> {log.purpose || 'NOT DECLARED'}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p style={{ textAlign: 'center', color: '#666', padding: 32 }}>
              No logs found matching filters.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}