import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'

function getMockRules() {
  return [
    { id: 1, gdpr_article: 'Art. 5', description: 'Bulk export of personal records without authorization', severity: 'CRITICAL', enabled: true },
    { id: 2, gdpr_article: 'Art. 6', description: 'Processing without valid lawful basis', severity: 'HIGH', enabled: true },
    { id: 3, gdpr_article: 'Art. 7', description: 'Processing after consent withdrawal', severity: 'CRITICAL', enabled: true },
    { id: 4, gdpr_article: 'Art. 9', description: 'Unauthorized access to special category data', severity: 'CRITICAL', enabled: true },
    { id: 5, gdpr_article: 'Art. 17', description: 'Failure to process erasure request within 30 days', severity: 'HIGH', enabled: true },
    { id: 6, gdpr_article: 'Art. 20', description: 'Denial of data portability request', severity: 'MEDIUM', enabled: true },
    { id: 7, gdpr_article: 'Art. 22', description: 'Automated decision without human review', severity: 'HIGH', enabled: false },
    { id: 8, gdpr_article: 'Art. 25', description: 'Access beyond role scope — data minimisation violation', severity: 'HIGH', enabled: true },
    { id: 9, gdpr_article: 'Art. 30', description: 'Processing activity not in Records of Processing', severity: 'MEDIUM', enabled: true },
    { id: 10, gdpr_article: 'Art. 32', description: 'After-hours access to sensitive data', severity: 'HIGH', enabled: true },
    { id: 11, gdpr_article: 'Art. 33', description: 'Data breach not reported within 72 hours', severity: 'CRITICAL', enabled: true },
    { id: 12, gdpr_article: 'Art. 37', description: 'No DPO designated for high-risk processing', severity: 'HIGH', enabled: false },
    { id: 13, gdpr_article: 'Art. 83', description: 'High penalty risk — repeated violations detected', severity: 'CRITICAL', enabled: true },
  ]
}

const severityColor = {
  CRITICAL: { bg: '#fff0f0', text: '#e53e3e' },
  HIGH: { bg: '#fff8e1', text: '#dd6b20' },
  MEDIUM: { bg: '#fffbeb', text: '#d69e2e' },
  LOW: { bg: '#f0fff4', text: '#38a169' }
}

export default function ConfigureRules() {
  const [rules, setRules] = useState([])
  const [search, setSearch] = useState('')

  useEffect(() => {
    api.get(`/rules/`)
      .then(r => setRules(r.data))
      .catch(() => setRules(getMockRules()))
  }, [])

  const filtered = rules.filter(r =>
    r.gdpr_article.toLowerCase().includes(search.toLowerCase()) ||
    r.description.toLowerCase().includes(search.toLowerCase())
  )

  const enabledCount = rules.filter(r => r.enabled).length

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="admin" />

      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* HEADER */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
            Configure Rules
          </h1>
          <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
            {enabledCount} of {rules.length} rules active.
          </p>
        </div>

        {/* SEARCH */}
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by article or description..."
          style={{
            width: '100%',
            padding: '10px 16px',
            border: '1px solid #ddd',
            borderRadius: 8,
            fontSize: 13,
            outline: 'none',
            marginBottom: 16,
            boxSizing: 'border-box',
            background: 'white'
          }}
        />

        {/* TABLE */}
        <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                {['Article', 'Description', 'Severity'].map(h => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      padding: '8px 14px',
                      fontSize: 11,
                      color: '#666',
                      letterSpacing: 0.5,
                      fontWeight: 600
                    }}
                  >
                    {h.toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {filtered.map(rule => (
                <tr
                  key={rule.id}
                  style={{
                    borderBottom: '1px solid #f0f0f0',
                    opacity: rule.enabled ? 1 : 0.5
                  }}
                >
                  <td style={{ padding: '12px 14px', fontWeight: 700, color: '#1a1a2e' }}>
                    {rule.gdpr_article}
                  </td>

                  <td style={{ padding: '12px 14px', color: '#555', maxWidth: 300 }}>
                    {rule.description}
                  </td>

                  <td style={{ padding: '12px 14px' }}>
                    <span
                      style={{
                        fontSize: 11,
                        padding: '3px 8px',
                        borderRadius: 4,
                        background: severityColor[rule.severity]?.bg,
                        color: severityColor[rule.severity]?.text,
                        fontWeight: 600
                      }}
                    >
                      {rule.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  )
}