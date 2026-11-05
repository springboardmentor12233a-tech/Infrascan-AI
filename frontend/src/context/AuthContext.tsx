import React, { createContext, useContext, useEffect, useState } from 'react'
import { authApi, usersApi, type User } from '../api/client'

interface AuthContextType {
  token: string | null
  role: string | null
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (fullName: string, email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('token'),
  )
  const [role, setRole] = useState<string | null>(localStorage.getItem('role'))
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })
  const [loading, setLoading] = useState<boolean>(true)

  // Fetch full user profile using current token
  const refreshUser = async () => {
    try {
      const userData = await usersApi.getMe()
      setUser(userData)
      setRole(userData.role)
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('role', userData.role)
    } catch {
      logout()
    }
  }

  // Load user data on startup if token is present
  useEffect(() => {
    if (token) {
      refreshUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  // Log in user
  const login = async (email: string, password: string) => {
    const tokenData = await authApi.login(email, password)
    localStorage.setItem('token', tokenData.access_token)
    localStorage.setItem('role', tokenData.role)
    setToken(tokenData.access_token)
    setRole(tokenData.role)

    // Fetch full profile immediately
    const profile = await usersApi.getMe()
    setUser(profile)
    localStorage.setItem('user', JSON.stringify(profile))
  }

  // Register new user (auto-role inspector)
  const register = async (
    fullName: string,
    email: string,
    password: string,
  ) => {
    await authApi.register(fullName, email, password)
    // Auto-login after registration
    await login(email, password)
  }

  // Clear auth state and local storage
  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('user')
    setToken(null)
    setRole(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        role,
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
