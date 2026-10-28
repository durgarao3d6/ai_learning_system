import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { authStore } from '../stores/authStore'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const client = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach Bearer token if present in authStore
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = authStore.getState().token
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Response interceptor: on 401, attempt token refresh using POST /api/v1/auth/refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: unknown) => void
  reject: (reason?: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      const url = originalRequest.url || ''
      // Avoid infinite loop if the 401 was from an auth endpoint itself
      if (
        url.includes('/api/v1/auth/login') ||
        url.includes('/api/v1/auth/register') ||
        url.includes('/api/v1/auth/refresh')
      ) {
        return Promise.reject(error)
      }

      originalRequest._retry = true
      const refreshToken = authStore.getState().refreshToken

      if (!refreshToken) {
        authStore.getState().logout()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((newToken) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
            }
            return client(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      isRefreshing = true

      try {
        const response = await axios.post<{ access_token: string; refresh_token?: string }>(
          `${baseURL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        )

        const newAccessToken = response.data.access_token
        const nextRefreshToken = response.data.refresh_token || refreshToken
        const currentUser = authStore.getState().user

        authStore.getState().login(newAccessToken, nextRefreshToken, currentUser)

        processQueue(null, newAccessToken)

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        }

        return client(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        authStore.getState().logout()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export const apiClient = client
export default client
