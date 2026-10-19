import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  allowedRoles?: string[]
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { token, role, loading } = useAuth()
  const location = useLocation()

  // Display minimal loading indicator while validating session
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-sm font-medium text-slate-500 animate-pulse">
          Loading authentication...
        </div>
      </div>
    )
  }

  // If not logged in, redirect to login page
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // If role is restricted and user does not have permission, redirect to dashboard
  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
