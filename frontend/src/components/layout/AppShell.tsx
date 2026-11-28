import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useAppStore } from '@/store/useAppStore'
import { authService } from '@/services/authService'
import { API_CONFIG } from '@/lib/constants'
import { tokenStorage } from '@/services/apiClient'

/**
 * AppShell — authenticated application wrapper.
 *
 * On mount, if a token exists in localStorage and mock mode is off,
 * validate it by calling /auth/me and hydrate the Zustand store.
 * This ensures a page refresh doesn't lose the authenticated user.
 */
export function AppShell() {
  const setCurrentUser = useAppStore((s) => s.setCurrentUser)
  const setAuthenticated = useAppStore((s) => s.setAuthenticated)
  const clearAuth = useAppStore((s) => s.clearAuth)

  useEffect(() => {
    if (API_CONFIG.enableMockData) return
    const token = tokenStorage.get()
    if (!token) {
      clearAuth()
      return
    }
    authService.getCurrentUser().then((user) => {
      if (user) {
        setCurrentUser(user)
        setAuthenticated(true)
      } else {
        clearAuth()
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen flex bg-[#F8FAFC] text-slate-900">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-4 lg:p-6 max-w-[1600px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
