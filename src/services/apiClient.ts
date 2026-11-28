import axios from 'axios'
import type { AxiosError } from 'axios'
import { API_CONFIG } from '@/lib/constants'

const TOKEN_KEY = 'infrascan_access_token'

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export const apiClient = axios.create({
  baseURL: API_CONFIG.baseUrl,
  timeout: API_CONFIG.timeoutMs,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor: attach Bearer token ──────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.get()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: global 401 handling ────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      tokenStorage.clear()
      // Avoid redirect loop on the login page itself
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

/** Extract a human-readable message from an Axios error. */
export function extractApiError(err: unknown): string {
  if (!err || typeof err !== 'object') return 'An unexpected error occurred.'
  const axiosErr = err as AxiosError<{ detail?: string | { msg: string }[] }>
  const detail = axiosErr.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  if (axiosErr.message === 'Network Error') return 'Cannot reach server. Check your connection or backend URL.'
  if (axiosErr.code === 'ECONNABORTED') return 'Request timed out. The server took too long to respond.'
  return axiosErr.message || 'An unexpected error occurred.'
}
