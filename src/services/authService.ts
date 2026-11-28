import { apiClient, tokenStorage, extractApiError } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_USERS } from '@/data/mockData'
import type { UserAccount } from '@/types'

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  name: string
  email: string
  password: string
  role?: string
  department?: string
}

/** Shape returned by POST /auth/login and /auth/register */
interface TokenPairResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: string
    full_name: string
    email: string
    role: string
    is_active: boolean
    created_at: string
  }
}

function mapApiUser(u: TokenPairResponse['user']): UserAccount {
  return {
    id: u.id,
    name: u.full_name,
    email: u.email,
    role: (u.role as UserAccount['role']) || 'Civil Engineer',
    department: 'Infrastructure Engineering',
    status: u.is_active ? 'Active' : 'Inactive',
    lastActive: u.created_at,
    avatarInitials: u.full_name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2),
  }
}

export const authService = {
  async login(payload: LoginPayload): Promise<{ user: UserAccount; token: string }> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 450))
      const matched = MOCK_USERS.find((u) => u.email.toLowerCase() === payload.email.toLowerCase()) || MOCK_USERS[0]
      const token = 'demo-jwt-token-infrascan'
      tokenStorage.set(token)
      return { user: matched, token }
    }
    try {
      const { data } = await apiClient.post<TokenPairResponse>('/auth/login', {
        email: payload.email,
        password: payload.password,
      })
      tokenStorage.set(data.access_token)
      return { user: mapApiUser(data.user), token: data.access_token }
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async register(payload: RegisterPayload): Promise<{ user: UserAccount; token: string }> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 500))
      const newUser: UserAccount = {
        id: `USR-${Math.floor(10 + Math.random() * 90)}`,
        name: payload.name,
        email: payload.email,
        role: (payload.role as UserAccount['role']) || 'Civil Engineer',
        department: payload.department || 'Structural Engineering',
        status: 'Active',
        lastActive: new Date().toISOString(),
        avatarInitials: payload.name
          .split(' ')
          .map((n) => n[0])
          .join('')
          .toUpperCase()
          .slice(0, 2),
      }
      const token = 'demo-jwt-token-infrascan'
      tokenStorage.set(token)
      return { user: newUser, token }
    }
    try {
      const { data } = await apiClient.post<TokenPairResponse>('/auth/register', {
        full_name: payload.name,
        email: payload.email,
        password: payload.password,
        role: payload.role || 'Engineer',
      })
      tokenStorage.set(data.access_token)
      return { user: mapApiUser(data.user), token: data.access_token }
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async getCurrentUser(): Promise<UserAccount | null> {
    if (API_CONFIG.enableMockData) {
      return null
    }
    try {
      const { data } = await apiClient.get<TokenPairResponse['user']>('/auth/me')
      return mapApiUser(data)
    } catch {
      return null
    }
  },

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 400))
      return { message: `Password reset instructions sent to ${email} (Demo mode).` }
    }
    try {
      const { data } = await apiClient.post<{ message: string }>('/auth/forgot-password', { email })
      return data
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  logout() {
    tokenStorage.clear()
  },
}
