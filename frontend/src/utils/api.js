import axios from 'axios'
import {
  getAccessToken,
  clearTokens
} from './auth'


const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})


// ========================================
// ATTACH ACCESS TOKEN TO EVERY REQUEST
// ========================================

api.interceptors.request.use(
  (config) => {

    const token = getAccessToken()

    console.log('API REQUEST:', {
      url: config.url,
      hasToken: !!token,
    })

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },

  (error) => {
    return Promise.reject(error)
  }
)


// ========================================
// HANDLE RESPONSE
// ========================================

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken()

    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }

    console.log('==============================')
    console.log('API REQUEST:', config.url)
    console.log('TOKEN EXISTS:', !!token)
    console.log(
      'AUTH HEADER:',
      config.headers?.Authorization ? 'Bearer TOKEN PRESENT' : 'NO AUTH HEADER'
    )
    console.log('==============================')

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)


export default api