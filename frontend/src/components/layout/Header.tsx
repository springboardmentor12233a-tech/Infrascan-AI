import { useState } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { Bell, Search, Menu, ChevronRight, LogOut, Settings, User } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'

const ROUTE_TITLES: Record<string, string> = {
  '/app/dashboard': 'Infrastructure Overview',
  '/app/assets': 'Asset Registry',
  '/app/inspections': 'Inspections',
  '/app/images': 'Image Repository',
  '/app/analysis': 'AI Damage Analysis',
  '/app/visualization': 'Damage Visualization',
  '/app/models': 'Model Performance',
  '/app/mapping': 'Geospatial Mapping',
  '/app/progression': 'Damage Progression',
  '/app/analytics': 'Analytics',
  '/app/maintenance': 'Maintenance Management',
  '/app/reports': 'Inspection Reports',
  '/app/notifications': 'Notifications',
  '/app/users': 'User Management',
  '/app/settings': 'Settings',
}

export function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { setMobileMenuOpen, currentUser, notifications, markAllNotificationsRead } = useAppStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [showNotifMenu, setShowNotifMenu] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)

  const unreadCount = notifications.filter((n) => !n.read).length
  const pageTitle = ROUTE_TITLES[location.pathname] || 'Workspace'

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    navigate(`/app/assets?q=${encodeURIComponent(searchQuery.trim())}`)
  }

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={() => setMobileMenuOpen(true)}
          className="lg:hidden p-2 rounded-md text-slate-600 hover:bg-slate-100"
          aria-label="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>
        <nav className="flex items-center gap-1.5 text-sm min-w-0">
          <Link to="/app/dashboard" className="text-slate-400 hover:text-slate-600 hidden sm:inline">
            InfraScan
          </Link>
          <ChevronRight className="w-4 h-4 text-slate-300 hidden sm:inline shrink-0" />
          <span className="font-semibold text-slate-900 truncate">{pageTitle}</span>
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <form onSubmit={handleSearch} className="hidden md:flex items-center relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search assets, IDs, inspections..."
            className="w-64 pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-600/20 focus:border-cyan-600"
          />
        </form>

        <div className="relative">
          <button
            onClick={() => {
              setShowNotifMenu(!showNotifMenu)
              setShowUserMenu(false)
            }}
            className="relative p-2 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-red-600 text-white text-[10px] font-semibold flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifMenu && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg border border-slate-200 shadow-lg z-40 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-900">Notifications ({unreadCount} unread)</span>
                <button
                  onClick={markAllNotificationsRead}
                  className="text-[11px] text-cyan-700 hover:underline font-medium"
                >
                  Mark all read
                </button>
              </div>
              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                {notifications.slice(0, 4).map((n) => (
                  <Link
                    key={n.id}
                    to="/app/notifications"
                    onClick={() => setShowNotifMenu(false)}
                    className="block px-4 py-3 hover:bg-slate-50 transition-colors"
                  >
                    <p className="text-xs font-medium text-slate-900">{n.title}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>
                  </Link>
                ))}
              </div>
              <Link
                to="/app/notifications"
                onClick={() => setShowNotifMenu(false)}
                className="block text-center py-2 text-xs font-medium text-cyan-700 bg-slate-50 hover:bg-slate-100 border-t border-slate-100"
              >
                View all notifications
              </Link>
            </div>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => {
              setShowUserMenu(!showUserMenu)
              setShowNotifMenu(false)
            }}
            className="flex items-center gap-2 pl-2 pr-1.5 py-1 rounded-md hover:bg-slate-100 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-[#0F2942] text-white flex items-center justify-center text-xs font-semibold">
              {currentUser.avatarInitials}
            </div>
            <span className="hidden sm:inline text-xs font-medium text-slate-700">{currentUser.name}</span>
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-lg border border-slate-200 shadow-lg z-40 py-1">
              <div className="px-3 py-2 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-900">{currentUser.name}</p>
                <p className="text-[11px] text-slate-500">{currentUser.email}</p>
              </div>
              <Link
                to="/app/settings"
                onClick={() => setShowUserMenu(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
              >
                <User className="w-3.5 h-3.5" /> Profile
              </Link>
              <Link
                to="/app/settings"
                onClick={() => setShowUserMenu(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
              >
                <Settings className="w-3.5 h-3.5" /> Settings
              </Link>
              <Link
                to="/login"
                onClick={() => {
                  localStorage.removeItem('infrascan_token')
                  setShowUserMenu(false)
                }}
                className="flex items-center gap-2 px-3 py-2 text-xs text-red-600 hover:bg-red-50 border-t border-slate-100"
              >
                <LogOut className="w-3.5 h-3.5" /> Sign Out
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
