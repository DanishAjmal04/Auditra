import { useState, useEffect } from 'react'
import Sidebar from '../../components/Sidebar'
import api from '../../utils/axios'

export default function ManageUsers() {
  const [users, setUsers] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form, setForm] = useState({
    name: '', email: '', role: 'COMPLIANCE_OFFICER', password: ''
  })
  const [message, setMessage] = useState(null)

  useEffect(() => { fetchUsers() }, [])

  function fetchUsers() {
    api.get('/admin/users/')
      .then(r => setUsers(r.data))
      .catch(() => setUsers([]))
  }

  function showMsg(type, text) {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  function handleCreate(e) {
    e.preventDefault()
    api.post('/admin/users/create/', form)
      .then(() => {
        fetchUsers()
        setForm({ name: '', email: '', role: 'COMPLIANCE_OFFICER', password: '' })
        setShowForm(false)
        showMsg('success', 'User created successfully.')
      })
      .catch(err => {
        const errors = err.response?.data
        const msg = errors
          ? Object.values(errors).flat().join(' ')
          : 'Failed to create user.'
        showMsg('error', msg)
      })
  }

  function handleEdit(user) {
    setEditingUser(user)
    setForm({
      name: user.name,
      email: user.email,
      role: user.role,
      password: ''
    })
    setShowForm(true)
  }

  function handleUpdate(e) {
    e.preventDefault()
    const data = { role: form.role }
    if (form.password) data.password = form.password

    api.patch(`/admin/users/${editingUser.id}/`, data)
      .then(() => {
        fetchUsers()
        setShowForm(false)
        setEditingUser(null)
        setForm({ name: '', email: '', role: 'COMPLIANCE_OFFICER', password: '' })
        showMsg('success', 'User updated successfully.')
      })
      .catch(() => showMsg('error', 'Failed to update user.'))
  }

  function handleToggleStatus(user) {
    const newStatus = user.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
    api.patch(`/admin/users/${user.id}/`, { status: newStatus })
      .then(() => {
        fetchUsers()
        showMsg('success', `User ${newStatus === 'ACTIVE' ? 'activated' : 'deactivated'}.`)
      })
      .catch(() => showMsg('error', 'Failed to update status.'))
  }

  function handleDelete(id) {
    if (!window.confirm('Delete this user permanently?')) return
    api.delete(`/admin/users/${id}/`)
      .then(() => {
        fetchUsers()
        showMsg('error', 'User deleted.')
      })
      .catch(() => showMsg('error', 'Failed to delete user.'))
  }

  const roleLabel = {
    'COMPLIANCE_OFFICER': 'Compliance Officer',
    'ADMIN': 'Admin'
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f0f2f5' }}>
      <Sidebar role="admin" />
      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>

        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: 28
        }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 4px' }}>
              Manage Users
            </h1>
            <p style={{ fontSize: 13, color: '#666', margin: 0 }}>
              Create, edit and deactivate compliance officer accounts.
            </p>
          </div>
          <button
            onClick={() => {
              setShowForm(!showForm)
              setEditingUser(null)
              setForm({ name: '', email: '', role: 'COMPLIANCE_OFFICER', password: '' })
            }}
            style={{
              padding: '10px 20px', background: '#1a1a2e',
              color: 'white', border: 'none', borderRadius: 8,
              fontSize: 13, fontWeight: 600, cursor: 'pointer'
            }}
          >
            {showForm ? 'Cancel' : '+ New User'}
          </button>
        </div>

        {/* Message */}
        {message && (
          <div style={{
            background: message.type === 'success' ? '#f0fff4' : '#fff0f0',
            border: `1px solid ${message.type === 'success' ? '#9ae6b4' : '#feb2b2'}`,
            borderRadius: 10, padding: '12px 18px', marginBottom: 20
          }}>
            <p style={{
              margin: 0, fontSize: 14, fontWeight: 500,
              color: message.type === 'success' ? '#276749' : '#c53030'
            }}>
              {message.text}
            </p>
          </div>
        )}

        {/* Form */}
        {showForm && (
          <div style={{
            background: 'white', borderRadius: 12,
            padding: 24, marginBottom: 24
          }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 20px' }}>
              {editingUser ? 'Edit User' : 'Create New Account'}
            </h3>
            <form onSubmit={editingUser ? handleUpdate : handleCreate}>
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr',
                gap: 16, marginBottom: 16
              }}>
                {!editingUser && (
                  <>
                    <div>
                      <label style={{
                        fontSize: 12, fontWeight: 600,
                        color: '#444', display: 'block', marginBottom: 6
                      }}>
                        FULL NAME
                      </label>
                      <input
                        required
                        value={form.name}
                        onChange={e => setForm({ ...form, name: e.target.value })}
                        placeholder="e.g. Sara Ahmed"
                        style={{
                          width: '100%', padding: '10px 12px',
                          border: '1px solid #ddd', borderRadius: 8,
                          fontSize: 13, outline: 'none', boxSizing: 'border-box'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{
                        fontSize: 12, fontWeight: 600,
                        color: '#444', display: 'block', marginBottom: 6
                      }}>
                        EMAIL
                      </label>
                      <input
                        required
                        type="email"
                        value={form.email}
                        onChange={e => setForm({ ...form, email: e.target.value })}
                        placeholder="sara@auditra.com"
                        style={{
                          width: '100%', padding: '10px 12px',
                          border: '1px solid #ddd', borderRadius: 8,
                          fontSize: 13, outline: 'none', boxSizing: 'border-box'
                        }}
                      />
                    </div>
                  </>
                )}

                <div>
                  <label style={{
                    fontSize: 12, fontWeight: 600,
                    color: '#444', display: 'block', marginBottom: 6
                  }}>
                    PASSWORD {editingUser && '(leave blank to keep current)'}
                  </label>
                  <input
                    type="password"
                    required={!editingUser}
                    value={form.password}
                    onChange={e => setForm({ ...form, password: e.target.value })}
                    placeholder="••••••••"
                    style={{
                      width: '100%', padding: '10px 12px',
                      border: '1px solid #ddd', borderRadius: 8,
                      fontSize: 13, outline: 'none', boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{
                    fontSize: 12, fontWeight: 600,
                    color: '#444', display: 'block', marginBottom: 6
                  }}>
                    ROLE
                  </label>
                  <select
                    value={form.role}
                    onChange={e => setForm({ ...form, role: e.target.value })}
                    style={{
                      width: '100%', padding: '10px 12px',
                      border: '1px solid #ddd', borderRadius: 8,
                      fontSize: 13, outline: 'none',
                      background: 'white', boxSizing: 'border-box'
                    }}
                  >
                    <option value="COMPLIANCE_OFFICER">Compliance Officer</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </div>
              </div>

              <button type="submit" style={{
                padding: '10px 24px', background: '#38a169',
                color: 'white', border: 'none', borderRadius: 8,
                fontSize: 13, fontWeight: 600, cursor: 'pointer'
              }}>
                {editingUser ? 'Save Changes' : 'Create Account'}
              </button>
            </form>
          </div>
        )}

        {/* Users Table */}
        <div style={{ background: 'white', borderRadius: 12, padding: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                {['User', 'Email', 'Role', 'Status', 'Actions'].map(h => (
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
              {users.map(u => (
                <tr key={u.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 34, height: 34, borderRadius: '50%',
                        background: '#1a1a2e', color: 'white',
                        display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: 12, fontWeight: 700
                      }}>
                        {u.name?.split(' ').map(n => n[0]).join('') || '?'}
                      </div>
                      <span style={{ fontWeight: 600 }}>{u.name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px', color: '#555' }}>{u.email}</td>
                  <td style={{ padding: '12px 14px' }}>
                    <span style={{
                      fontSize: 11, padding: '3px 8px', borderRadius: 4,
                      background: '#ede9fe', color: '#6b46c1', fontWeight: 600
                    }}>
                      {roleLabel[u.role] || u.role}
                    </span>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <span style={{
                      fontSize: 11, padding: '3px 8px', borderRadius: 4,
                      background: u.status === 'ACTIVE' ? '#f0fff4' : '#f0f0f0',
                      color: u.status === 'ACTIVE' ? '#38a169' : '#888',
                      fontWeight: 600
                    }}>
                      {u.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        onClick={() => handleEdit(u)}
                        style={{
                          padding: '4px 10px', background: '#ede9fe',
                          color: '#6b46c1', border: '1px solid #6b46c1',
                          borderRadius: 4, fontSize: 11,
                          cursor: 'pointer', fontWeight: 600
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleToggleStatus(u)}
                        style={{
                          padding: '4px 10px',
                          background: u.status === 'ACTIVE' ? '#fff8e1' : '#f0fff4',
                          color: u.status === 'ACTIVE' ? '#dd6b20' : '#38a169',
                          border: '1px solid',
                          borderColor: u.status === 'ACTIVE' ? '#dd6b20' : '#38a169',
                          borderRadius: 4, fontSize: 11,
                          cursor: 'pointer', fontWeight: 600
                        }}
                      >
                        {u.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        onClick={() => handleDelete(u.id)}
                        style={{
                          padding: '4px 10px', background: '#fff0f0',
                          color: '#e53e3e', border: '1px solid #e53e3e',
                          borderRadius: 4, fontSize: 11,
                          cursor: 'pointer', fontWeight: 600
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <p style={{ textAlign: 'center', color: '#666', padding: 32 }}>
              No users found.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}