import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage, RegisterPage, ForgotPasswordPage } from '@/pages/AuthPages'
import { DashboardPage } from '@/pages/DashboardPage'
import { AssetsPage } from '@/pages/AssetsPage'
import { AssetFormPage } from '@/pages/AssetFormPage'
import { AssetDetailsPage } from '@/pages/AssetDetailsPage'
import { InspectionsPage } from '@/pages/InspectionsPage'
import { InspectionWizardPage } from '@/pages/InspectionWizardPage'
import { InspectionDetailsPage } from '@/pages/InspectionDetailsPage'
import { ImageRepositoryPage } from '@/pages/ImageRepositoryPage'
import { ImageUploadPage } from '@/pages/ImageUploadPage'
import { ImageDetailsPage } from '@/pages/ImageDetailsPage'
import { AiAnalysisPage } from '@/pages/AiAnalysisPage'
import { AnalysisDashboardPage } from '@/pages/AnalysisDashboardPage'
import { NewAnalysisPage } from '@/pages/NewAnalysisPage'
import { DamageVisualizationPage } from '@/pages/DamageVisualizationPage'
import { GeospatialMappingPage } from '@/pages/GeospatialMappingPage'
import { DamageProgressionPage } from '@/pages/DamageProgressionPage'
import { AnalyticsPage, ModelPerformancePage } from '@/pages/AnalyticsPage'
import { MaintenancePage } from '@/pages/MaintenancePage'
import { ReportsPage } from '@/pages/ReportsPage'
import { NotificationsPage } from '@/pages/NotificationsPage'
import { UserManagementPage } from '@/pages/UserManagementPage'
import { SettingsPage } from '@/pages/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/capabilities" element={<LandingPage />} />
          <Route path="/how-it-works" element={<LandingPage />} />
          <Route path="/technology" element={<LandingPage />} />
          <Route path="/infrastructure" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />

          {/* Authenticated App Shell (/app/*) */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="assets" element={<AssetsPage />} />
            <Route path="assets/new" element={<AssetFormPage />} />
            <Route path="assets/:id" element={<AssetDetailsPage />} />
            <Route path="assets/:id/edit" element={<AssetFormPage />} />
            <Route path="inspections" element={<InspectionsPage />} />
            <Route path="inspections/new" element={<InspectionWizardPage />} />
            <Route path="inspections/:id" element={<InspectionDetailsPage />} />
            <Route path="inspections/:id/edit" element={<InspectionDetailsPage initialTab="overview" />} />
            <Route path="inspections/:id/images" element={<InspectionDetailsPage initialTab="images" />} />
            <Route path="images" element={<ImageRepositoryPage />} />
            <Route path="images/upload" element={<ImageUploadPage />} />
            <Route path="images/:id" element={<ImageDetailsPage />} />
            <Route path="images/:id/edit" element={<ImageDetailsPage />} />
            <Route path="analysis" element={<AnalysisDashboardPage />} />
            <Route path="analysis/new" element={<NewAnalysisPage />} />
            <Route path="analysis/history" element={<AnalysisDashboardPage />} />
            <Route path="analysis/:id" element={<AiAnalysisPage />} />
            <Route path="analysis/:id/results" element={<AiAnalysisPage />} />
            <Route path="visualization" element={<DamageVisualizationPage />} />
            <Route path="visualization/:analysisId" element={<DamageVisualizationPage />} />
            <Route path="models" element={<ModelPerformancePage />} />
            <Route path="mapping" element={<GeospatialMappingPage />} />
            <Route path="progression" element={<DamageProgressionPage />} />
            <Route path="progression/:assetId" element={<DamageProgressionPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="maintenance" element={<MaintenancePage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="users" element={<UserManagementPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Legacy/Shortcut Redirects */}
          <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
          <Route path="/assets" element={<Navigate to="/app/assets" replace />} />
          <Route path="/inspections" element={<Navigate to="/app/inspections" replace />} />
          <Route path="/images" element={<Navigate to="/app/images" replace />} />
          <Route path="/analysis" element={<Navigate to="/app/analysis" replace />} />
          <Route path="/visualization" element={<Navigate to="/app/visualization" replace />} />
          <Route path="/model-performance" element={<Navigate to="/app/models" replace />} />
          <Route path="/mapping" element={<Navigate to="/app/mapping" replace />} />
          <Route path="/progression" element={<Navigate to="/app/progression" replace />} />
          <Route path="/analytics" element={<Navigate to="/app/analytics" replace />} />
          <Route path="/maintenance" element={<Navigate to="/app/maintenance" replace />} />
          <Route path="/reports" element={<Navigate to="/app/reports" replace />} />
          <Route path="/notifications" element={<Navigate to="/app/notifications" replace />} />
          <Route path="/users" element={<Navigate to="/app/users" replace />} />
          <Route path="/settings" element={<Navigate to="/app/settings" replace />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
