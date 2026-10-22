import axios from 'axios'

const BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
const ACCESS = 'auditra.access'
const REFRESH = 'auditra.refresh'

function read(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function write(key, value) {
  try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key) } catch { /* private mode */ }
}

export const tokens = {
  access: () => read(ACCESS),
  refresh: () => read(REFRESH),
  save(access, refresh) { write(ACCESS, access); if (refresh) write(REFRESH, refresh) },
  clear() { write(ACCESS, null); write(REFRESH, null) },
}

const api = axios.create({ baseURL: BASE })

api.interceptors.request.use((config) => {
  const token = tokens.access()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing = null
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const url = original?.url || ''
    if (error.response?.status === 401 && original && !original._retry && !url.includes('/auth/')) {
      original._retry = true
      const refresh = tokens.refresh()
      if (refresh) {
        try {
          refreshing = refreshing || axios.post(`${BASE}/auth/refresh/`, { refresh }).finally(() => { refreshing = null })
          const { data } = await refreshing
          tokens.save(data.access, data.refresh)
          original.headers.Authorization = `Bearer ${data.access}`
          return api(original)
        } catch { /* fall through to logout */ }
      }
      tokens.clear()
      if (!window.location.pathname.startsWith('/login')) window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export function errorText(error, fallback = 'Something went wrong') {
  const data = error?.response?.data
  if (!data) return error?.message || fallback
  if (typeof data === 'string') return data.slice(0, 200)
  if (data.error) return data.error
  if (data.detail) return data.detail
  const first = Object.entries(data)[0]
  if (first) return `${first[0]}: ${Array.isArray(first[1]) ? first[1].join(' ') : first[1]}`
  return fallback
}

export async function download(path, filename) {
  const response = await api.get(path, { responseType: 'blob' })
  const href = URL.createObjectURL(response.data)
  const link = Object.assign(document.createElement('a'), { href, download: filename })
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

export const list = (data) => (Array.isArray(data) ? data : data?.results || [])

export default api
