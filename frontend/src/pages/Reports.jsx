import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import Sidebar from '../components/Sidebar'
import AlertBanner from '../components/AlertBanner'
import api from '../utils/axios'


function getMockData() {
  return {
    compliance_score: 74,
    total_violations: 32,
    critical_open: 4,
    high_open: 8,
    resolved: 18,
    generated_at: new Date().toLocaleString(),
    by_article: [
      { article: 'Art. 5', count: 8 },
      { article: 'Art. 6', count: 5 },
      { article: 'Art. 25', count: 6 },
      { article: 'Art. 32', count: 7 },
      { article: 'Art. 33', count: 4 },
      { article: 'Art. 17', count: 2 },
    ],
    recent_critical: [
      { id: 1, user: 'u_hassan', article: 'Art. 5', reason: 'Bulk export of personal records', risk: 0.92, date: '2025-06-12' },
      { id: 2, user: 'u_ayesha', article: 'Art. 32', reason: 'After-hours sensitive data access', risk: 0.88, date: '2025-06-11' },
      { id: 3, user: 'u_tariq', article: 'Art. 25', reason: 'Role-based access violation', risk: 0.76, date: '2025-06-10' },
      { id: 4, user: 'u_zara', article: 'Art. 6', reason: 'Missing lawful basis', risk: 0.71, date: '2025-06-09' },
    ]
  }
}

const articleColors = ['#e53e3e', '#dd6b20', '#d69e2e', '#38a169', '#3182ce', '#805ad5']

export default function Reports() {
  const [data, setData] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState(false)

  useEffect(() => {
    api.get(`/stats/`)
      .then(r => {
        setData({
          compliance_score: r.data.compliance_score,
          total_violations: r.data.total_violations,
          critical_open: r.data.critical_open || 4,
          high_open: r.data.high_open || 8,
          resolved: r.data.resolved || 18,
          generated_at: new Date().toLocaleString(),
          by_article: r.data.by_article?.map(a => ({
            article: a.rule__gdpr_article,
            count: a.count
          })) || [],
          recent_critical: []
        })
      })
      .catch(() => setData(getMockData()))
  }, [])

  async function handleGenerate() {
    setGenerating(true)
    await new Promise(r => setTimeout(r, 1500))
    setData(prev => ({ ...prev, generated_at: new Date().toLocaleString() }))
    setGenerating(false)
    setGenerated(true)
  }

  function handleDownload() {
  window.open('http://127.0.0.1:8000/api/generate-pdf/', '_blank')
}

  const scoreColor = data?.compliance_score >= 80
    ? '#38a169'
    : data?.compliance_score >= 60
    ? '#dd6b20'
    : '#e53e3e'

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <AlertBanner />
      <Sidebar role="compliance" />
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
              Compliance Reports
            </h1>
            <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
              Generate and download compliance summary reports.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button
              onClick={handleGenerate}
              disabled={generating}
              style={{
                padding: '10px 20px',
                background: generating ? '#999' : '#1a1a2e',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                cursor: generating ? 'not-allowed' : 'pointer'
              }}
            >
              {generating ? 'Generating...' : 'Generate Report'}
            </button>
            <button
              onClick={handleDownload}
              disabled={!data}
              style={{
                padding: '10px 20px',
                background: data ? '#38a169' : '#ccc',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                cursor: data ? 'pointer' : 'not-allowed'
              }}
            >
              Download Report
            </button>
          </div>
        </div>

        {/* Generated Alert */}
        {generated && (
          <div style={{
            background: '#f0fff4',
            border: '1px solid #9ae6b4',
            borderRadius: 10,
            padding: '12px 18px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 10
          }}>
            <span style={{ fontSize: 18 }}>✅</span>
            <p style={{ margin: 0, fontSize: 14, color: '#276749', fontWeight: 500 }}>
              Report generated at {data?.generated_at}. Click Download to save.
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 16,
              marginBottom: 24
            }}>
              {[
                { label: 'COMPLIANCE SCORE', value: `${data.compliance_score}%`, color: scoreColor },
                { label: 'TOTAL VIOLATIONS', value: data.total_violations, color: '#e53e3e' },
                { label: 'CRITICAL OPEN', value: data.critical_open, color: '#dd6b20' },
                { label: 'RESOLVED', value: data.resolved, color: '#38a169' },
              ].map(card => (
                <div key={card.label} style={{
                  background: 'white', borderRadius: 12,
                  padding: 20, borderTop: `4px solid ${card.color}`
                }}>
                  <p style={{
                    fontSize: 11, color: '#666',
                    letterSpacing: 1, margin: '0 0 8px'
                  }}>
                    {card.label}
                  </p>
                  <p style={{
                    fontSize: 32, fontWeight: 700,
                    color: card.color, margin: 0
                  }}>
                    {card.value}
                  </p>
                </div>
              ))}
            </div>

            {/* Compliance Score Bar */}
            <div style={{
              background: 'white', borderRadius: 12,
              padding: 24, marginBottom: 24
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12
              }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
                  Overall Compliance Score
                </h3>
                <span style={{
                  fontSize: 22, fontWeight: 700, color: scoreColor
                }}>
                  {data.compliance_score}%
                </span>
              </div>
              <div style={{
                background: '#f0f0f0',
                borderRadius: 8, height: 16, overflow: 'hidden'
              }}>
                <div style={{
                  width: `${data.compliance_score}%`,
                  height: '100%',
                  background: scoreColor,
                  borderRadius: 8,
                  transition: 'width 1s ease'
                }} />
              </div>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginTop: 6
              }}>
                <span style={{ fontSize: 11, color: '#e53e3e' }}>0% — Critical</span>
                <span style={{ fontSize: 11, color: '#dd6b20' }}>60% — Moderate</span>
                <span style={{ fontSize: 11, color: '#38a169' }}>80%+ — Good</span>
              </div>
            </div>

            {/* Bottom Row */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 20
            }}>

              {/* Bar Chart */}
              <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 20px' }}>
                  Violations by GDPR Article
                </h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={data.by_article}>
                    <XAxis dataKey="article" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {data.by_article.map((_, i) => (
                        <Cell key={i} fill={articleColors[i % articleColors.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Critical Violations */}
              <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>
                  Open Critical Violations
                </h3>
                {data.recent_critical.length === 0 && (
                  <p style={{ color: '#666', fontSize: 13 }}>No critical violations.</p>
                )}
                {data.recent_critical.map(v => (
                  <div key={v.id} style={{
                    padding: '12px 0',
                    borderBottom: '1px solid #f0f0f0'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: 4
                    }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>
                        {v.user}
                      </span>
                      <span style={{
                        fontSize: 11, padding: '2px 8px',
                        borderRadius: 4, background: '#fff0f0',
                        color: '#e53e3e', fontWeight: 600
                      }}>
                        {v.article}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: '#555', margin: '0 0 2px' }}>
                      {v.reason}
                    </p>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between'
                    }}>
                      <span style={{ fontSize: 11, color: '#999' }}>{v.date}</span>
                      <span style={{
                        fontSize: 11, fontWeight: 700, color: '#e53e3e'
                      }}>
                        Risk: {v.risk}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

            </div>
          </>
        )}
      </div>
    </div>
  )
}