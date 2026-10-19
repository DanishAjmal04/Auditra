import { Navigate, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'

import Dashboard from './pages/Dashboard'
import Violations from './pages/Violations'
import UserActivity from './pages/UserActivity'

import DeletionRequests from './pages/rights/DeletionRequests'
import ConsentManagement from './pages/rights/ConsentManagement'
import SubjectAccess from './pages/rights/SubjectAccess'

import Reports from './pages/Reports'
import DPO from './pages/DPO'
import RoPA from './pages/RoPA'

import AdminDashboard from './pages/admin/AdminDashboard'
import ManageUsers from './pages/admin/ManageUsers'
import ConfigureRules from './pages/admin/ConfigureRules'
import ViewLogs from './pages/admin/ViewLogs'
import SystemHealth from './pages/admin/SystemHealth'

import {
  getAccessToken,
  getRoleFromToken,
  isTokenExpired
} from './utils/auth'


// ============================================
// PROTECTED ROUTE
// ============================================

const ProtectedRoute = ({ children, requiredRole }) => {
  const token = getAccessToken()
  const expired = isTokenExpired()

  // No token OR token expired
  if (!token || expired) {
    return <Navigate to="/login" replace />
  }

  // Check role if route requires one
  if (requiredRole) {
    const role = getRoleFromToken()

    if (role !== requiredRole) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return children
}


// ============================================
// UNAUTHORIZED PAGE
// ============================================

function Unauthorized() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f8f9fa',
        fontFamily: 'Arial, sans-serif'
      }}
    >
      <h1
        style={{
          fontSize: 48,
          marginBottom: 10,
          color: '#1a1a2e'
        }}
      >
        403
      </h1>

      <h2
        style={{
          marginBottom: 10,
          color: '#333'
        }}
      >
        Unauthorized
      </h2>

      <p
        style={{
          color: '#666',
          marginBottom: 25
        }}
      >
        You do not have permission to access this page.
      </p>

      <button
        onClick={() => window.history.back()}
        style={{
          padding: '10px 20px',
          background: '#1a1a2e',
          color: 'white',
          border: 'none',
          borderRadius: 8,
          cursor: 'pointer',
          fontSize: 14
        }}
      >
        Go Back
      </button>
    </div>
  )
}


// ============================================
// APP
// ============================================

export default function App() {
  return (
    <Routes>

      {/* ================================
          PUBLIC ROUTES
      ================================= */}

      <Route
        path="/"
        element={<Navigate to="/login" replace />}
      />

      <Route
        path="/login"
        element={<Login />}
      />

      <Route
        path="/unauthorized"
        element={<Unauthorized />}
      />


      {/* ================================
          COMPLIANCE OFFICER ROUTES
      ================================= */}

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/violations"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <Violations />
          </ProtectedRoute>
        }
      />

      <Route
        path="/user-activity"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <UserActivity />
          </ProtectedRoute>
        }
      />

      <Route
        path="/rights/deletion"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <DeletionRequests />
          </ProtectedRoute>
        }
      />

      <Route
        path="/rights/consent"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <ConsentManagement />
          </ProtectedRoute>
        }
      />

      <Route
        path="/rights/access"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <SubjectAccess />
          </ProtectedRoute>
        }
      />

      <Route
        path="/reports"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <Reports />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dpo"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <DPO />
          </ProtectedRoute>
        }
      />

      <Route
        path="/ropa"
        element={
          <ProtectedRoute requiredRole="compliance_officer">
            <RoPA />
          </ProtectedRoute>
        }
      />


      {/* ================================
          ADMIN ROUTES
      ================================= */}

      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/users"
        element={
          <ProtectedRoute requiredRole="admin">
            <ManageUsers />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/rules"
        element={
          <ProtectedRoute requiredRole="admin">
            <ConfigureRules />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/logs"
        element={
          <ProtectedRoute requiredRole="admin">
            <ViewLogs />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/health"
        element={
          <ProtectedRoute requiredRole="admin">
            <SystemHealth />
          </ProtectedRoute>
        }
      />


      {/* ================================
          UNKNOWN ROUTE
      ================================= */}

      <Route
        path="*"
        element={<Navigate to="/login" replace />}
      />

    </Routes>
  )
}
