import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

import {
  saveTokens,
  getRoleFromToken,
  isTokenExpired
} from '../utils/auth'


export default function Login() {

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()


  async function handleLogin(e) {

    e.preventDefault()

    setLoading(true)
    setError('')

    try {

      const response = await axios.post(
        'http://127.0.0.1:8000/api/auth/login/',
        {
          username: username.trim(),
          password
        }
      )


      console.log('LOGIN RESPONSE:', response.data)


      const { access, refresh } = response.data


      // Make sure backend actually returned tokens
      if (!access || !refresh) {

        console.error(
          'Login response does not contain access/refresh:',
          response.data
        )

        setError('Login failed: JWT tokens were not returned.')

        return
      }


      // Save JWT tokens
      saveTokens(access, refresh)


      // Check token expiration
      if (isTokenExpired()) {

        console.error('Received JWT is already expired.')

        setError('Login failed: received token is expired.')

        return
      }


      // Get role from JWT
      const role = getRoleFromToken()


      console.log('JWT ROLE:', role)


      // Role missing from JWT
      if (!role) {

        console.error(
          'Role is missing from JWT payload.'
        )

        setError(
          'Login successful, but user role is missing from JWT.'
        )

        return
      }


      // =========================
      // ROLE BASED REDIRECT
      // =========================

      if (role === 'admin') {

        navigate('/admin/dashboard', {
          replace: true
        })

      }

      else if (role === 'compliance_officer') {

        navigate('/dashboard', {
          replace: true
        })

      }

      else {

        console.error('Unknown role:', role)

        setError(
          `Unknown user role: ${role}`
        )
      }


    } catch (err) {

      console.error('Login error:', err)

      console.error(
        'Backend response:',
        err.response?.data
      )


      setError(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Invalid credentials. Please try again.'
      )

    } finally {

      setLoading(false)

    }
  }


  return (

    <div style={{
      display: 'flex',
      height: '100vh'
    }}>

      {/* LEFT SIDE */}

      <div
        style={{
          width: '40%',
          background: '#1a1a2e',
          color: 'white',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '60px 50px'
        }}
      >

        <h1
          style={{
            fontSize: 32,
            fontWeight: 700,
            marginBottom: 8
          }}
        >
          Auditra
        </h1>


        <p
          style={{
            color: '#8892b0',
            fontSize: 13,
            letterSpacing: 2,
            marginBottom: 40
          }}
        >
          GDPR COMPLIANCE MONITOR
        </p>


        <h2
          style={{
            fontSize: 22,
            fontWeight: 600,
            marginBottom: 16,
            lineHeight: 1.4
          }}
        >
          Automated compliance monitoring for your organization
        </h2>


        <p
          style={{
            color: '#8892b0',
            fontSize: 14,
            lineHeight: 1.7,
            marginBottom: 32
          }}
        >
          Auditra continuously analyzes system access logs,
          detects GDPR violations, and generates audit-ready
          compliance reports.
        </p>


        {[
          'Rule-based GDPR checks',
          'One-Class SVM (CERT-trained) supporting detector',
          'Automated compliance reporting',
          'GDPR Article traceability'
        ].map((feature) => (

          <div
            key={feature}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              marginBottom: 12
            }}
          >

            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: '#4fc3f7'
              }}
            />

            <span
              style={{
                color: '#ccd6f6',
                fontSize: 14
              }}
            >
              {feature}
            </span>

          </div>

        ))}

      </div>


      {/* RIGHT SIDE */}

      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'white'
        }}
      >

        <div style={{ width: 400 }}>

          <h2
            style={{
              fontSize: 28,
              fontWeight: 700,
              marginBottom: 8
            }}
          >
            Welcome back
          </h2>


          <p
            style={{
              color: '#666',
              marginBottom: 32
            }}
          >
            Sign in to your Auditra account
          </p>


          {/* ERROR */}

          {error && (

            <div
              style={{
                background: '#fff0f0',
                border: '1px solid #ffcccc',
                color: '#cc0000',
                padding: '10px 14px',
                borderRadius: 8,
                marginBottom: 16,
                fontSize: 14
              }}
            >
              {error}
            </div>

          )}


          <form onSubmit={handleLogin}>

            {/* USERNAME */}

            <label
              style={{
                fontSize: 13,
                fontWeight: 500,
                display: 'block',
                marginBottom: 6
              }}
            >
              Username
            </label>


            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoComplete="username"
              style={{
                width: '100%',
                padding: '12px 14px',
                border: '1px solid #ddd',
                borderRadius: 8,
                fontSize: 14,
                marginBottom: 16,
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />


            {/* PASSWORD */}

            <label
              style={{
                fontSize: 13,
                fontWeight: 500,
                display: 'block',
                marginBottom: 6
              }}
            >
              Password
            </label>


            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
              style={{
                width: '100%',
                padding: '12px 14px',
                border: '1px solid #ddd',
                borderRadius: 8,
                fontSize: 14,
                marginBottom: 24,
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />


            {/* LOGIN BUTTON */}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '13px',
                background: loading ? '#999' : '#1a1a2e',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                fontSize: 15,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading
                ? 'Signing in...'
                : 'Sign In'
              }
            </button>

          </form>

        </div>

      </div>

    </div>
  )
}