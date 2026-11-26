import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

import Login from './pages/Login';
import Register from './pages/Register';
import UserDashboard from './pages/UserDashboard';
import AdminDashboard from './pages/AdminDashboard';
import NewInspection from './pages/NewInspection';
import InspectionsList from './pages/InspectionsList';
import InspectionDetail from './pages/InspectionDetail';
import Assets from './pages/Assets';
import MapView from './pages/MapView';
import ModelComparison from './pages/ModelComparison';

function RootRedirect() {
  const { user, isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return isAdmin ? <Navigate to="/admin/dashboard" replace /> : <Navigate to="/user/dashboard" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
        <Navbar />
        <main className="flex-1">
          <Routes>
            {/* Root & Public Authentication Routes */}
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dashboard" element={<RootRedirect />} />

            {/* Dedicated Registered User Experience */}
            <Route
              path="/user/dashboard"
              element={
                <ProtectedRoute>
                  <UserDashboard />
                </ProtectedRoute>
              }
            />

            {/* Dedicated Administrator Experience */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute adminOnly>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />

            {/* Shared Inspection & System Modules */}
            <Route
              path="/new-inspection"
              element={
                <ProtectedRoute>
                  <NewInspection />
                </ProtectedRoute>
              }
            />
            <Route
              path="/inspections"
              element={
                <ProtectedRoute>
                  <InspectionsList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/inspections/:id"
              element={
                <ProtectedRoute>
                  <InspectionDetail />
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
                  <MapView />
                </ProtectedRoute>
              }
            />
            <Route
              path="/models"
              element={
                <ProtectedRoute>
                  <ModelComparison />
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-center text-xs text-slate-500">
          InfraScan &mdash; AI-Powered Civil Infrastructure Crack & Damage Assessment Platform
        </footer>
      </div>
    </AuthProvider>
  );
}
