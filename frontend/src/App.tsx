import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Dashboard } from './pages/Dashboard'
import { Profile } from './pages/Profile'
import { Users } from './pages/Users'
import { Assets } from './pages/Assets'
import { AssetDetailPage } from './pages/AssetDetail'
import { Inspections } from './pages/Inspections'
import { Upload } from './pages/Upload'
import { InspectionDetailPage } from './pages/InspectionDetail'
import { MapPage } from './pages/Map'
import { ForgotPassword } from './pages/ForgotPassword'
import { ResetPassword } from './pages/ResetPassword'
import { Forbidden } from './pages/Forbidden'
import { AuditLogs } from './pages/AuditLogs'
import { Reports } from './pages/Reports'
import { Maintenance } from './pages/Maintenance'
import { Comparisons } from './pages/Comparisons'
import { Notifications } from './pages/Notifications'
import { Models } from './pages/Models'
import { Jobs } from './pages/Jobs'
import { About } from './pages/About'
import { Help } from './pages/Help'
import { NotFound } from './pages/NotFound'
import { ErrorBoundary } from './components/ErrorBoundary'

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public authentication routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/403" element={<Forbidden />} />
            <Route path="/about" element={<About />} />
            <Route path="/help" element={<Help />} />

          {/* Authenticated routes accessible to all roles */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assets"
            element={
              <ProtectedRoute>
                <Assets />
              </ProtectedRoute>
            }
          />
          <Route
            path="/map"
            element={
              <ProtectedRoute>
                <MapPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assets/:id"
            element={
              <ProtectedRoute>
                <AssetDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inspections"
            element={
              <ProtectedRoute>
                <Inspections />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute allowedRoles={['admin', 'manager', 'civil_engineer']}>
                <Reports />
              </ProtectedRoute>
            }
          />
          <Route
            path="/maintenance"
            element={
              <ProtectedRoute allowedRoles={['admin', 'manager', 'civil_engineer', 'maintenance_engineer']}>
                <Maintenance />
              </ProtectedRoute>
            }
          />
          <Route
            path="/comparisons"
            element={
              <ProtectedRoute allowedRoles={['admin', 'manager', 'civil_engineer']}>
                <Comparisons />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute>
                <Notifications />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inspections/:id"
            element={
              <ProtectedRoute>
                <InspectionDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/upload"
            element={
              <ProtectedRoute allowedRoles={['inspector', 'civil_engineer', 'manager', 'admin']}>
                <Upload />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />

          {/* Admin only routes */}
          <Route
            path="/users"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <Users />
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit-logs"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AuditLogs />
              </ProtectedRoute>
            }
          />
          <Route
            path="/models"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <Models />
              </ProtectedRoute>
            }
          />
          <Route
            path="/jobs"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <Jobs />
              </ProtectedRoute>
            }
          />

          {/* Fallback route */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </ErrorBoundary>
  )
}

export default App
