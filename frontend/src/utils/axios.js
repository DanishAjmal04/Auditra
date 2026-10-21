import axios from 'axios'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from './auth'

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshRequest = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    const url = original?.url || ''
    const isAuthCall = url.includes('/auth/login') || url.includes('/auth/refresh')

    if (status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true
      const refresh = getRefreshToken()
      if (!refresh) {
        clearTokens()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }

      try {
        if (!refreshRequest) {
          refreshRequest = axios
            .post('http://127.0.0.1:8000/api/auth/refresh/', { refresh })
            .finally(() => {
              refreshRequest = null
            })
        }
        const refreshed = await refreshRequest
        saveTokens(refreshed.data.access, refreshed.data.refresh || refresh)
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${refreshed.data.access}`
        return api(original)
      } catch (refreshError) {
        clearTokens()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      }
    }

    if (status === 401 && window.location.pathname !== '/login') {
      clearTokens()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export async function downloadAuthenticated(path, filename) {
  const response = await api.get(path, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default api
