import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { AssetList } from './pages/AssetList';
import { AssetForm } from './pages/AssetForm';
import { AssetDetail } from './pages/AssetDetail';
import { InspectionView } from './pages/InspectionView';
import { UserManagement } from './pages/UserManagement';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Application Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/assets" element={<AssetList />} />
              <Route path="/assets/:id" element={<AssetDetail />} />
              <Route path="/inspections/:id" element={<InspectionView />} />

              {/* Manager & Admin Only Asset Modifications */}
              <Route
                element={
                  <ProtectedRoute allowedRoles={['Administrator', 'Infrastructure Manager']} />
                }
              >
                <Route path="/assets/new" element={<AssetForm />} />
                <Route path="/assets/:id/edit" element={<AssetForm />} />
              </Route>

              {/* Administrator Only User Console */}
              <Route element={<ProtectedRoute allowedRoles={['Administrator']} />}>
                <Route path="/admin/users" element={<UserManagement />} />
              </Route>
            </Route>
          </Route>

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
