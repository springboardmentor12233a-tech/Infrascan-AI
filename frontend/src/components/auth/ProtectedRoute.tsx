import { Navigate, useLocation } from 'react-router-dom'
import { useAppStore } from '@/store/useAppStore'
import { API_CONFIG } from '@/lib/constants'

interface ProtectedRouteProps {
  children: React.ReactNode
}

/**
 * Wraps any route that requires authentication.
 *
 * In mock-data mode, all routes are always accessible (demo experience).
 * In live API mode, unauthenticated users are redirected to /login with
 * the original destination preserved via React Router `state.from`.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated)
  const location = useLocation()

  // Demo / mock mode: skip auth check so the app works without a backend
  if (API_CONFIG.enableMockData) {
    return <>{children}</>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

