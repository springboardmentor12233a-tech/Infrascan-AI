import { create } from 'zustand'
import type { UserAccount, AppNotification } from '@/types'
import { MOCK_USERS, MOCK_NOTIFICATIONS } from '@/data/mockData'
import { tokenStorage } from '@/services/apiClient'

interface AppState {
  sidebarCollapsed: boolean
  mobileMenuOpen: boolean
  currentUser: UserAccount
  isAuthenticated: boolean
  notifications: AppNotification[]
  toggleSidebar: () => void
  setMobileMenuOpen: (open: boolean) => void
  setCurrentUser: (user: UserAccount) => void
  setAuthenticated: (authenticated: boolean) => void
  clearAuth: () => void
  markNotificationRead: (id: string) => void
  markAllNotificationsRead: () => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  mobileMenuOpen: false,
  currentUser: MOCK_USERS[0],
  isAuthenticated: !!tokenStorage.get(),
  notifications: MOCK_NOTIFICATIONS,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
  setCurrentUser: (user) => set({ currentUser: user }),
  setAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),
  clearAuth: () => {
    tokenStorage.clear()
    set({ isAuthenticated: false, currentUser: MOCK_USERS[0] })
  },
  markNotificationRead: (id) =>
    set((s) => ({
      notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
    })),
  markAllNotificationsRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
    })),
}))
