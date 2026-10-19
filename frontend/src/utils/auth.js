const TOKEN_KEY = 'auditra_access'
const REFRESH_KEY = 'auditra_refresh'


// ===============================
// SAVE TOKENS
// ===============================

export const saveTokens = (access, refresh) => {
  if (!access || !refresh) {
    console.error('JWT tokens missing:', { access, refresh })
    return
  }

  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}


// ===============================
// GET TOKENS
// ===============================

export const getAccessToken = () => {
  return localStorage.getItem(TOKEN_KEY)
}

export const getRefreshToken = () => {
  return localStorage.getItem(REFRESH_KEY)
}


// ===============================
// CLEAR TOKENS
// ===============================

export const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}


// ===============================
// DECODE JWT
// ===============================

export const decodeToken = (token = getAccessToken()) => {
  if (!token) {
    return null
  }

  try {
    const parts = token.split('.')

    // JWT should have exactly 3 parts
    if (parts.length !== 3) {
      console.error('Invalid JWT format')
      return null
    }

    let base64 = parts[1]

    // Convert Base64URL -> Base64
    base64 = base64.replace(/-/g, '+').replace(/_/g, '/')

    // Add required padding
    while (base64.length % 4 !== 0) {
      base64 += '='
    }

    const decoded = atob(base64)

    return JSON.parse(decoded)

  } catch (error) {
    console.error('JWT decode error:', error)
    return null
  }
}


// ===============================
// GET ROLE
// ===============================

export const getRoleFromToken = () => {
  const payload = decodeToken()

  if (!payload) {
    return null
  }

  return payload.role || null
}


// ===============================
// CHECK TOKEN EXPIRATION
// ===============================

export const isTokenExpired = () => {
  const payload = decodeToken()

  if (!payload) {
    return true
  }

  // If JWT has no exp claim
  if (!payload.exp) {
    console.warn('JWT does not contain exp claim')
    return false
  }

  return payload.exp * 1000 <= Date.now()
}


// ===============================
// CHECK AUTHENTICATION
// ===============================

export const isAuthenticated = () => {
  const token = getAccessToken()

  if (!token) {
    return false
  }

  return !isTokenExpired()
}