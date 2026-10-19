import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'


function getMockData() {
  return [
    { id: 1, user_id: 'user_1042', purpose: 'Marketing emails', lawful_basis: 'CONSENT', declared_at: '2024-01-15', is_valid: false, active_processing: true },
    { id: 2, user_id: 'user_0893', purpose: 'Analytics tracking', lawful_basis: 'CONSENT', declared_at: '2024-03-20', is_valid: false, active_processing: true },
    { id: 3, user_id: 'user_1187', purpose: 'Payroll processing', lawful_basis: 'CONTRACT', declared_at: '2023-09-01', is_valid: true, active_processing: true },
    { id: 4, user_id: 'user_0654', purpose: 'Third party sharing', lawful_basis: 'CONSENT', declared_at: '2024-02-10', is_valid: false, active_processing: false },
    { id: 5, user_id: 'user_1301', purpose: 'Product recommendations', lawful_basis: 'LEGITIMATE_INTEREST', declared_at: '2023-11-05', is_valid: true, active_processing: true },
    { id: 6, user_id: 'user_0421', purpose: 'Customer support logs', lawful_basis: 'CONTRACT', declared_at: '2023-07-22', is_valid: true, active_processing: true },
    { id: 7, user_id: 'user_0992', purpose: 'Newsletter subscription', lawful_basis: 'CONSENT', declared_at: '2024-04-01', is_valid: false, active_processing: true },
  ]
}

export default function ConsentManagement() {
  const [records, setRecords] = useState([])
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    api.get(`/consent-records/`)
      .then(r => setRecords(r.data))
      .catch(() => setRecords(getMockData()))
  }, [])

  const withdrawn = records.filter(r => !r.is_valid && r.lawful_basis === 'CONSENT')
  const activeWithdrawn = records.filter(r => !r.is_valid && r.active_processing)
  const valid = records.filter(r => r.is_valid)

  const filtered = records.filter(r => {
    if (filter === 'ALL') return true
    if (filter === 'WITHDRAWN') return !r.is_valid
    if (filter === 'FLAGGED') return !r.is_valid && r.active_processing
    if (filter === 'VALID') return r.is_valid
    return true
  })

  const basisColor = {
    CONSENT: '#3182ce',
    CONTRACT: '#38a169',
    LEGITIMATE_INTEREST: '#dd6b20',
    LEGAL_OBLIGATION: '#805ad5'
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="compliance" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
            Consent Management
          </h1>
          <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
            GDPR Art. 6 & 7 — Lawful basis verification and consent tracking.
          </p>
        </div>

        {/* Summary Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          marginBottom: 24
        }}>
          {[
            { label: 'WITHDRAWN CONSENT', value: withdrawn.length, color: '#e53e3e' },
            { label: 'ACTIVE PROCESSING (FLAGGED)', value: activeWithdrawn.length, color: '#dd6b20' },
            { label: 'VALID RECORDS', value: valid.length, color: '#38a169' },
          ].map(card => (
            <div key={card.label} style={{
              background: 'white', borderRadius: 12,
              padding: 20, borderTop: `4px solid ${card.color}`
            }}>
              <p style={{ fontSize: 11, color: '#666', letterSpacing: 1, margin: '0 0 8px' }}>
                {card.label}
              </p>
              <p style={{ fontSize: 36, fontWeight: 700, color: card.color, margin: 0 }}>
                {card.value}
              </p>
            </div>
          ))}
        </div>

        {/* Flagged Alert */}
        {activeWithdrawn.length > 0 && (
          <div style={{
            background: '#fff0f0',
            border: '1px solid #feb2b2',
            borderRadius: 10,
            padding: '14px 18px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 12
          }}>
            <span style={{ fontSize: 20 }}>🚨</span>
            <div>
              <p style={{ fontWeight: 600, color: '#e53e3e', margin: '0 0 2px', fontSize: 14 }}>
                {activeWithdrawn.length} users have withdrawn consent but processing continues
              </p>
              <p style={{ fontSize: 12, color: '#c53030', margin: 0 }}>
                This is a GDPR violation — processing must stop immediately.
              </p>
            </div>
          </div>
        )}

        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {['ALL', 'WITHDRAWN', 'FLAGGED', 'VALID'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                border: '1px solid',
                borderColor: filter === f ? '#1a1a2e' : '#ddd',
                background: filter === f ? '#1a1a2e' : 'white',
                color: filter === f ? 'white' : '#555',
                fontSize: 12,
                fontWeight: filter === f ? 600 : 400,
                cursor: 'pointer'
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Table */}
        <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                {['User', 'Purpose', 'Lawful Basis', 'Declared', 'Consent Status', 'Active Processing', 'Risk'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '8px 14px',
                    fontSize: 11, color: '#666',
                    letterSpacing: 0.5, fontWeight: 600
                  }}>
                    {h.toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(rec => {
                const isFlagged = !rec.is_valid && rec.active_processing
                return (
                  <tr key={rec.id} style={{
                    background: isFlagged ? '#fff0f0' : !rec.is_valid ? '#fff8f8' : 'white',
                    borderBottom: '1px solid #f0f0f0'
                  }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600 }}>
                      {rec.user_id}
                    </td>
                    <td style={{ padding: '12px 14px', color: '#555' }}>
                      {rec.purpose}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontSize: 11, padding: '3px 8px', borderRadius: 4,
                        background: (basisColor[rec.lawful_basis] || '#888') + '20',
                        color: basisColor[rec.lawful_basis] || '#888',
                        fontWeight: 600
                      }}>
                        {rec.lawful_basis?.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', color: '#555' }}>
                      {rec.declared_at}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontSize: 11, padding: '3px 8px', borderRadius: 4,
                        background: rec.is_valid ? '#f0fff4' : '#fff0f0',
                        color: rec.is_valid ? '#38a169' : '#e53e3e',
                        fontWeight: 600
                      }}>
                        {rec.is_valid ? 'VALID' : 'WITHDRAWN'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontSize: 11, padding: '3px 8px', borderRadius: 4,
                        background: rec.active_processing ? '#fff8e1' : '#f0f0f0',
                        color: rec.active_processing ? '#dd6b20' : '#888',
                        fontWeight: 600
                      }}>
                        {rec.active_processing ? 'ACTIVE' : 'STOPPED'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      {isFlagged ? (
                        <span style={{
                          fontSize: 11, padding: '3px 8px', borderRadius: 4,
                          background: '#fff0f0', color: '#e53e3e', fontWeight: 700
                        }}>
                          🚨 VIOLATION
                        </span>
                      ) : (
                        <span style={{ fontSize: 11, color: '#38a169', fontWeight: 600 }}>
                          ✓ OK
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}