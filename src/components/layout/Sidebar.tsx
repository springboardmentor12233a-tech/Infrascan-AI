import { NavLink, useNavigate } from 'react-router-dom'
import { authService } from '@/services/authService'
import {
  LayoutDashboard,
  Building2,
  ClipboardCheck,
  Images,
  ScanSearch,
  Layers,
  Activity,
  MapPin,
  TrendingUp,
  BarChart3,
  Wrench,
  FileText,
  Bell,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  LogOut,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/store/useAppStore'

const NAV_GROUPS = [
  {
    label: 'OVERVIEW',
    items: [{ to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'INFRASTRUCTURE',
    items: [
      { to: '/app/assets', label: 'Asset Registry', icon: Building2 },
      { to: '/app/inspections', label: 'Inspections', icon: ClipboardCheck },
      { to: '/app/images', label: 'Image Repository', icon: Images },
    ],
  },
  {
    label: 'AI INTELLIGENCE',
    items: [
      { to: '/app/analysis', label: 'AI Damage Analysis', icon: ScanSearch },
      { to: '/app/visualization', label: 'Damage Visualization', icon: Layers },
      { to: '/app/models', label: 'Model Performance', icon: Activity },
    ],
  },
  {
    label: 'MONITORING',
    items: [
      { to: '/app/mapping', label: 'Geospatial Mapping', icon: MapPin },
      { to: '/app/progression', label: 'Damage Progression', icon: TrendingUp },
      { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'OPERATIONS',
    items: [
      { to: '/app/maintenance', label: 'Maintenance Management', icon: Wrench },
      { to: '/app/reports', label: 'Inspection Reports', icon: FileText },
      { to: '/app/notifications', label: 'Notifications', icon: Bell },
    ],
  },
  {
    label: 'ADMINISTRATION',
    items: [
      { to: '/app/users', label: 'User Management', icon: Users },
      { to: '/app/settings', label: 'Settings', icon: Settings },
    ],
  },
]

export function Sidebar() {
  const navigate = useNavigate()
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen, currentUser, clearAuth } = useAppStore()

  const handleLogout = () => {
    authService.logout()
    clearAuth()
    setMobileMenuOpen(false)
    navigate('/login')
  }

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#0B162C] text-slate-300 border-r border-slate-800">
      {/* Brand */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80 shrink-0">
        <NavLink to="/" className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-md bg-cyan-600 flex items-center justify-center text-white shrink-0">
            <ShieldAlert className="w-5 h-5" />
          </div>
          {!sidebarCollapsed && (
            <div className="leading-tight">
              <span className="font-semibold text-white tracking-tight text-sm block">InfraScan</span>
              <span className="text-[10px] text-cyan-400 font-medium tracking-wider uppercase">
                AI Infrastructure Intelligence
              </span>
            </div>
          )}
        </NavLink>
        <button
          onClick={toggleSidebar}
          className="hidden lg:flex p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
        <button
          onClick={() => setMobileMenuOpen(false)}
          className="lg:hidden p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
          aria-label="Close menu"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2.5 space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {!sidebarCollapsed && (
              <p className="px-2.5 mb-1.5 text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    title={sidebarCollapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 px-2.5 py-2 rounded-md text-[13px] font-medium transition-colors',
                        isActive
                          ? 'bg-cyan-600/15 text-cyan-300 border-l-2 border-cyan-400'
                          : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
                      )
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User Profile & Logout */}
      <div className="p-3 border-t border-slate-800/80 shrink-0 flex items-center justify-between gap-2">
        <NavLink
          to="/app/settings"
          onClick={() => setMobileMenuOpen(false)}
          className="flex items-center gap-2.5 p-1.5 rounded-md hover:bg-slate-800/70 transition-colors min-w-0 flex-1"
        >
          <div className="w-8 h-8 rounded-full bg-slate-700 text-cyan-300 flex items-center justify-center text-xs font-semibold shrink-0">
            {currentUser.avatarInitials}
          </div>
          {!sidebarCollapsed && (
            <div className="min-w-0">
              <p className="text-xs font-medium text-white truncate">{currentUser.name}</p>
              <p className="text-[11px] text-slate-400 truncate">{currentUser.role}</p>
            </div>
          )}
        </NavLink>
        {!sidebarCollapsed && (
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-2 rounded-md text-slate-400 hover:text-red-400 hover:bg-slate-800/70 transition-colors shrink-0"
            aria-label="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )

  return (
    <>
      <aside
        className={cn(
          'hidden lg:block shrink-0 transition-all duration-200',
          sidebarCollapsed ? 'w-[68px]' : 'w-64'
        )}
      >
        <div className="fixed top-0 left-0 bottom-0 z-30" style={{ width: sidebarCollapsed ? 68 : 256 }}>
          {sidebarContent}
        </div>
      </aside>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div className="fixed inset-0 bg-slate-900/60" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative w-64 max-w-[80vw] h-full z-10">{sidebarContent}</div>
        </div>
      )}
    </>
  )
}
