import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Violations from './pages/Violations'

export default function App() {
  const isLoggedIn = localStorage.getItem('auditra_auth')

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={isLoggedIn ? <Dashboard /> : <Navigate to="/login" />} />
      <Route path="/violations" element={isLoggedIn ? <Violations /> : <Navigate to="/login" />} />
    </Routes>
  )
}