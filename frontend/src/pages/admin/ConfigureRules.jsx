import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'

const severityColor = {
  CRITICAL: { bg: '#fff0f0', text: '#e53e3e' },
  HIGH: { bg: '#fff8e1', text: '#dd6b20' },
  MEDIUM: { bg: '#fffbeb', text: '#d69e2e' },
  LOW: { bg: '#f0fff4', text: '#38a169' }
}

export default function ConfigureRules() {
  const [rules, setRules] = useState([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/rules/')
      .then(response => setRules(response.data))
      .catch(() => setError('Could not load rules.'))
  }, [])

  function toggleRule(rule) {
    api.patch(`/rules/${rule.id}/`, { enabled: !rule.enabled })
      .then(response => {
        setRules(current => current.map(item => item.id === rule.id ? response.data : item))
        setError('')
      })
      .catch(() => setError('Could not update that rule.'))
  }

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
            {enabledCount} of {rules.length} rules active. Disabled rules are not checked.
          </p>
        </div>
        {error && <p style={{ color: '#e53e3e', marginBottom: 12 }}>{error}</p>}

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
                {['Article', 'Description', 'Severity', 'Enabled'].map(h => (
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
                  <td style={{ padding: '12px 14px' }}>
                    <button
                      onClick={() => toggleRule(rule)}
                      style={{
                        fontSize: 12,
                        padding: '4px 10px',
                        borderRadius: 4,
                        border: '1px solid #ddd',
                        background: rule.enabled ? '#f0fff4' : '#fff0f0',
                        color: rule.enabled ? '#38a169' : '#e53e3e',
                        cursor: 'pointer',
                        fontWeight: 600,
                      }}
                    >
                      {rule.enabled ? 'Enabled' : 'Disabled'}
                    </button>
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