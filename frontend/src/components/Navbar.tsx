import React, { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { notificationsApi, type NotificationItem } from '../api/client'

export const Navbar: React.FC = () => {
  const { user, role, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [showNotifs, setShowNotifs] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    if (user) {
      notificationsApi.list(false).then((data) => {
        setNotifications(data || [])
        setUnreadCount((data || []).filter((n) => !n.is_read).length)
      }).catch(() => {})
    }
  }, [user, location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const markAllRead = async () => {
    for (const n of notifications.filter((x) => !x.is_read)) {
      await notificationsApi.markRead(n.notification_id).catch(() => {})
    }
    setUnreadCount(0)
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
  }

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="sticky top-0 z-50 bg-[#141619]/90 backdrop-blur-md border-b border-[rgba(179,180,189,0.12)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / Brand */}
          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="flex items-center space-x-3 group">
              <div className="w-8 h-8 rounded-lg bg-[#3D52A0] flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(112,145,230,0.6)] group-hover:scale-105 transition-transform border border-[#7091E6]/40">
                IS
              </div>
              <span className="text-xl font-bold tracking-tight text-white">
                Infra<span className="text-[#7091E6]">Scan</span>
              </span>
            </Link>

            {/* Navigation links */}
            <nav className="flex items-center space-x-2">
              <Link
                to="/dashboard"
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                  isActive('/dashboard')
                    ? 'bg-[#0A21C0] text-white shadow-[0_0_12px_rgba(10,33,192,0.5)]'
                    : 'text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A]'
                }`}
              >
                Dashboard
              </Link>

              <Link
                to="/assets"
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                  isActive('/assets') || location.pathname.startsWith('/assets/')
                    ? 'bg-[#0A21C0] text-white shadow-[0_0_12px_rgba(10,33,192,0.5)]'
                    : 'text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A]'
                }`}
              >
                Assets
              </Link>

              <Link
                to="/inspections"
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                  isActive('/inspections') || location.pathname.startsWith('/inspections/')
                    ? 'bg-[#0A21C0] text-white shadow-[0_0_12px_rgba(10,33,192,0.5)]'
                    : 'text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A]'
                }`}
              >
                Inspections
              </Link>

              {(role === 'inspector' || role === 'civil_engineer' || role === 'admin') && (
                <Link
                  to="/upload"
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    isActive('/upload')
                      ? 'bg-[#0A21C0] text-white shadow-[0_0_12px_rgba(10,33,192,0.5)]'
                      : 'text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A]'
                  }`}
                >
                  Upload & AI
                </Link>
              )}

              {role === 'admin' && (
                <Link
                  to="/users"
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    isActive('/users')
                      ? 'bg-[#0A21C0] text-white shadow-[0_0_12px_rgba(10,33,192,0.5)]'
                      : 'text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A]'
                  }`}
                >
                  Users
                </Link>
              )}
            </nav>
          </div>

          {/* Right controls */}
          <div className="flex items-center space-x-3">
            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A] transition-colors cursor-pointer"
              title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
              aria-label="Toggle Light and Dark Theme"
            >
              {theme === 'dark' ? (
                /* Sun Icon for Light mode */
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                /* Moon Icon for Dark mode */
                <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>

            {/* Notification Bell */}
            <div className="relative">
              <button
                onClick={() => setShowNotifs(!showNotifs)}
                className="relative p-2 rounded-full text-[#B3B4BD] hover:text-white hover:bg-[#2C2E3A] transition-colors"
                title="Notifications"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-rose-500 rounded-full animate-pulse"></span>
                )}
              </button>

              {/* Notification Dropdown */}
              {showNotifs && (
                <div className="absolute right-0 mt-2 w-80 bg-[#2C2E3A] border border-[rgba(179,180,189,0.2)] rounded-2xl shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-[rgba(179,180,189,0.15)]">
                    <span className="font-semibold text-white text-sm">System Alerts</span>
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllRead}
                        className="text-xs text-[#0A21C0] hover:underline"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {notifications.length === 0 ? (
                      <p className="text-xs text-[#B3B4BD] py-4 text-center">No notifications at this time.</p>
                    ) : (
                      notifications.slice(0, 5).map((n) => (
                        <div
                          key={n.notification_id}
                          className={`p-2.5 rounded-xl border text-xs ${
                            n.is_read
                              ? 'bg-[#141619]/40 border-transparent text-[#B3B4BD]'
                              : 'bg-[#141619] border-[rgba(10,33,192,0.4)] text-white shadow-sm'
                          }`}
                        >
                          <div className="flex items-center justify-between font-semibold mb-1">
                            <span>{n.title}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                              n.severity === 'critical' || n.severity === 'high' ? 'bg-rose-500/20 text-rose-300' : 'bg-blue-500/20 text-blue-300'
                            }`}>
                              {n.severity}
                            </span>
                          </div>
                          <p className="text-[#B3B4BD] line-clamp-2">{n.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* User Profile Info */}
            {user && (
              <div className="flex items-center space-x-3">
                <Link to="/profile" className="flex items-center space-x-2 text-right group">
                  <div className="w-8 h-8 rounded-full bg-[#2C2E3A] border border-[rgba(179,180,189,0.25)] flex items-center justify-center font-bold text-white text-xs group-hover:border-[#0A21C0] transition-colors">
                    {user.full_name ? user.full_name.slice(0, 2).toUpperCase() : 'US'}
                  </div>
                  <div className="hidden sm:block text-left">
                    <p className="text-xs font-semibold text-white group-hover:text-[#0A21C0] transition-colors">
                      {user.full_name}
                    </p>
                    <span className="text-[10px] text-[#B3B4BD] uppercase tracking-wider block">
                      {user.role.replace('_', ' ')}
                    </span>
                  </div>
                </Link>

                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 rounded-full text-xs font-medium text-[#B3B4BD] hover:text-white hover:bg-rose-500/20 hover:border-rose-500/40 border border-transparent transition-all"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
