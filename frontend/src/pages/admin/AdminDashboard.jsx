import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'


function getMockData() {
  return {
    total_users: 12,
    active_rules: 20,
    total_logs: 8400,
    total_violations: 32,
    compliance_score: 74,
    by_article: [
      { article: 'Art. 5', count: 8 },
      { article: 'Art. 6', count: 5 },
      { article: 'Art. 25', count: 6 },
      { article: 'Art. 32', count: 7 },
      { article: 'Art. 33', count: 4 },
    ],
    recent_users: [
      { id: 1, name: 'Sara Ahmed', email: 'sara@auditra.com', role: 'Compliance Officer', status: 'ACTIVE' },
      { id: 2, name: 'Ali Raza', email: 'ali@auditra.com', role: 'Compliance Officer', status: 'ACTIVE' },
      { id: 3, name: 'Maria Khan', email: 'maria@auditra.com', role: 'Compliance Officer', status: 'INACTIVE' },
    ]
  }
}

const articleColors = ['#e53e3e', '#dd6b20', '#d69e2e', '#38a169', '#3182ce']

export default function AdminDashboard() {
  const [data, setData] = useState(null)

  useEffect(() => {
    api.get(`/admin/stats/`)
      .then(r => setData(r.data))
      .catch(() => setData(getMockData()))
  }, [])

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="admin" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
            Admin Dashboard
          </h1>
          <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
            System overview and management.
          </p>
        </div>

        {data && (
          <>
            {/* Stat Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 16,
              marginBottom: 24
            }}>
              {[
                { label: 'TOTAL USERS', value: data.total_users, color: '#3182ce' },
                { label: 'ACTIVE RULES', value: data.active_rules, color: '#805ad5' },
                { label: 'TOTAL LOGS', value: data.total_logs.toLocaleString(), color: '#dd6b20' },
                { label: 'COMPLIANCE SCORE', value: `${data.compliance_score}%`, color: '#38a169' },
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

              {/* Recent Users */}
              <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 16
                }}>
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>
                    Recent Users
                  </h3>
                  <a href="/admin/users" style={{
                    fontSize: 13, color: '#3182ce',
                    textDecoration: 'none'
                  }}>
                    Manage all
                  </a>
                </div>
                {data.recent_users.map(u => (
                  <div key={u.id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 0',
                    borderBottom: '1px solid #f0f0f0'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: '50%',
                        background: '#1a1a2e', color: 'white',
                        display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: 13, fontWeight: 700
                      }}>
                        {u.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 500, margin: 0 }}>
                          {u.name}
                        </p>
                        <p style={{ fontSize: 11, color: '#666', margin: '2px 0 0' }}>
                          {u.email}
                        </p>
                      </div>
                    </div>
                    <span style={{
                      fontSize: 11, padding: '3px 8px', borderRadius: 4,
                      background: u.status === 'ACTIVE' ? '#f0fff4' : '#f0f0f0',
                      color: u.status === 'ACTIVE' ? '#38a169' : '#888',
                      fontWeight: 600
                    }}>
                      {u.status}
                    </span>
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