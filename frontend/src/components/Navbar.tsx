import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export const Navbar: React.FC = () => {
  const { user, role, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="bg-slate-900 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / Brand */}
          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-white">
                Infra<span className="text-indigo-400">Scan</span>
              </span>
            </Link>

            {/* Role-based navigation links */}
            <nav className="flex space-x-3">
              {/* Dashboard is visible to all authenticated users */}
              <Link
                to="/dashboard"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/dashboard')
                    ? 'bg-slate-800 text-indigo-400'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                Dashboard
              </Link>

              {/* Assets management is visible to all authenticated roles */}
              <Link
                to="/assets"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/assets') || location.pathname.startsWith('/assets/')
                    ? 'bg-slate-800 text-indigo-400'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                Assets
              </Link>

              {/* Inspections is visible to all authenticated roles */}
              <Link
                to="/inspections"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/inspections') || location.pathname.startsWith('/inspections/')
                    ? 'bg-slate-800 text-indigo-400'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                Inspections
              </Link>

              {/* Upload is visible to inspector, civil_engineer, and admin */}
              {(role === 'inspector' || role === 'civil_engineer' || role === 'admin') && (
                <Link
                  to="/upload"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/upload')
                      ? 'bg-slate-800 text-indigo-400'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  Upload
                </Link>
              )}

              {/* Users management page is only visible to admin */}
              {role === 'admin' && (
                <Link
                  to="/users"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/users')
                      ? 'bg-slate-800 text-indigo-400'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  Users
                </Link>
              )}

              {/* Profile is visible to all authenticated users */}
              <Link
                to="/profile"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/profile')
                    ? 'bg-slate-800 text-indigo-400'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                Profile
              </Link>
            </nav>
          </div>

          {/* User information and logout button */}
          <div className="flex items-center space-x-4">
            {user && (
              <div className="flex items-center space-x-3 text-right">
                <div>
                  <p className="text-sm font-medium text-slate-100">
                    {user.full_name}
                  </p>
                  <span className="inline-block px-2 py-0.5 text-xs font-semibold rounded bg-indigo-900 text-indigo-300 uppercase tracking-wider">
                    {user.role.replace('_', ' ')}
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-md text-sm font-medium text-slate-300 hover:bg-rose-900/60 hover:text-rose-200 transition-colors border border-slate-700 hover:border-rose-800"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
