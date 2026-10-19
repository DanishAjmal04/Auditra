import { Link, useLocation, useNavigate } from 'react-router-dom'
import api from '../utils/api'
import { clearTokens, getRefreshToken } from '../utils/auth'


const complianceLinks = [
  {
    section: 'MONITOR',
    links: [
      { to: '/dashboard', label: 'Dashboard' },
      { to: '/violations', label: 'Violations' },
      { to: '/user-activity', label: 'User Activity' },
    ]
  },
  {
    section: 'RIGHTS',
    links: [
      { to: '/rights/deletion', label: 'Deletion Requests' },
      { to: '/rights/consent', label: 'Consent Management' },
      { to: '/rights/access', label: 'Subject Access' },
    ]
  },
  {
    section: 'ANALYZE',
    links: [
      { to: '/reports', label: 'Reports' },
      { to: '/dpo', label: 'DPO Verification' },
      { to: '/ropa', label: 'RoPA Register' },
    ]
  },
]


const adminLinks = [
  {
    section: 'SYSTEM',
    links: [
      { to: '/admin/dashboard', label: 'Dashboard' },
      { to: '/admin/users', label: 'Manage Users' },
      { to: '/admin/rules', label: 'Configure Rules' },
      { to: '/admin/logs', label: 'View All Logs' },
      { to: '/admin/health', label: 'System Health' },
    ]
  },
]


export default function Sidebar({ role = 'compliance' }) {
  const location = useLocation()
  const navigate = useNavigate()

  const links = role === 'admin' ? adminLinks : complianceLinks

  const userName =
    role === 'admin'
      ? 'Administrator'
      : 'Compliance Officer'


  // ============================================
  // LOGOUT
  // ============================================

  async function handleLogout() {
    try {
      const refreshToken = getRefreshToken()

      // Only call backend if refresh token exists
      if (refreshToken) {
        await api.post('/auth/logout/', {
          refresh: refreshToken
        })
      }

    } catch (error) {
      // Even if backend logout/blacklist fails,
      // we still clear tokens locally.
      console.error('Logout error:', error)

    } finally {
      // Remove access + refresh tokens
      clearTokens()

      // Go back to login page
      navigate('/login', { replace: true })
    }
  }


  return (
    <div
      style={{
        width: 220,
        background: '#1a1a2e',
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px 0',
        minHeight: '100vh',
        flexShrink: 0
      }}
    >

      {/* ============================================
          LOGO
      ============================================ */}

      <div
        style={{
          padding: '0 24px 24px',
          borderBottom: '1px solid #2d2d44'
        }}
      >
        <h2
          style={{
            fontSize: 20,
            fontWeight: 700,
            margin: 0
          }}
        >
          Auditra
        </h2>

        <p
          style={{
            fontSize: 10,
            color: '#8892b0',
            letterSpacing: 1.5,
            margin: '4px 0 0'
          }}
        >
          COMPLIANCE MONITOR
        </p>
      </div>


      {/* ============================================
          NAVIGATION LINKS
      ============================================ */}

      <nav
        style={{
          padding: '16px 0',
          flex: 1
        }}
      >
        {links.map((section) => (
          <div key={section.section}>

            {/* Section title */}
            <p
              style={{
                padding: '12px 24px 6px',
                fontSize: 10,
                color: '#8892b0',
                letterSpacing: 1.5,
                margin: 0
              }}
            >
              {section.section}
            </p>


            {/* Section links */}
            {section.links.map((link) => {

              const isActive =
                location.pathname === link.to

              return (
                <Link
                  key={link.to}
                  to={link.to}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '10px 24px',
                    color: isActive
                      ? 'white'
                      : '#8892b0',
                    textDecoration: 'none',
                    fontSize: 14,
                    background: isActive
                      ? '#2d2d44'
                      : 'transparent',
                    borderLeft: isActive
                      ? '3px solid #4fc3f7'
                      : '3px solid transparent'
                  }}
                >
                  {link.label}
                </Link>
              )
            })}

          </div>
        ))}
      </nav>


      {/* ============================================
          USER + LOGOUT
      ============================================ */}

      <div
        style={{
          padding: '16px 24px',
          borderTop: '1px solid #2d2d44'
        }}
      >

        <p
          style={{
            fontSize: 13,
            fontWeight: 500,
            margin: 0
          }}
        >
          {userName}
        </p>


        <button
          onClick={handleLogout}
          style={{
            marginTop: 8,
            background: 'none',
            border: '1px solid #444',
            color: '#8892b0',
            padding: '4px 12px',
            borderRadius: 4,
            fontSize: 12,
            cursor: 'pointer'
          }}
        >
          Logout
        </button>

      </div>

    </div>
  )
}
