import React, { useState, useEffect, useRef } from 'react';
import { NavLink, Outlet, useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import { NotificationItem } from '../types';
import { 
  Building2, 
  Users, 
  LayoutDashboard, 
  LogOut, 
  HardHat,
  Wrench,
  BarChart2,
  Cpu,
  ChevronRight,
  ShieldCheck,
  Sparkles,
  Bell,
  Check,
  AlertTriangle,
  ShieldAlert,
  Info,
  Clock,
  ExternalLink,
  X,
  Layers,
  Activity,
  Menu
} from 'lucide-react';

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Notification drawer state
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      const res = await api.get('/notifications');
      const list = res.data || [];
      setNotifications(list);
      setUnreadCount(list.filter((n: NotificationItem) => !n.is_read).length);
    } catch (e) {
      // silently ignore if auth not ready
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 15000);
    return () => clearInterval(interval);
  }, []);

  // Close notifications dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close mobile menu on location change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleMarkAllRead = async () => {
    try {
      await api.put('/notifications/read-all');
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNotificationClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await api.put(`/notifications/${notif.id}/read`);
        setNotifications(notifications.map(n => n.id === notif.id ? { ...n, is_read: true } : n));
        setUnreadCount(Math.max(0, unreadCount - 1));
      } catch (e) {}
    }
    if (notif.link) {
      setShowNotifMenu(false);
      navigate(notif.link);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isAdmin = user?.role?.name === 'Administrator';

  // Compute page title from path
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/dashboard') return 'Structural Health Dashboard';
    if (path === '/assets') return 'Civil Infrastructure Assets';
    if (path.startsWith('/assets/new')) return 'Register Infrastructure Asset';
    if (path.startsWith('/assets/')) return 'Asset Specifications & History';
    if (path.startsWith('/inspections/')) return 'Inspection Workspace & AI Analysis';
    if (path === '/maintenance') return 'Maintenance Priority & Work Orders';
    if (path === '/model-comparison') return 'AI Models & Benchmarking';
    if (path === '/admin/users') return 'User & Role Management';
    return 'Infrastructure Management';
  };

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/assets', label: 'Infrastructure Assets', icon: Building2 },
    { to: '/maintenance', label: 'Maintenance & Work Orders', icon: Wrench },
    { to: '/model-comparison', label: 'AI Models & Benchmark', icon: BarChart2 },
    ...(isAdmin ? [{ to: '/admin/users', label: 'User Management', icon: Users }] : []),
  ];

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-800 antialiased font-sans">
      {/* ── Sidebar (Desktop) ────────────────────────────────────────────── */}
      <aside className="hidden lg:flex w-64 bg-slate-900 text-slate-200 flex-col shrink-0 border-r border-slate-800/90 shadow-sm z-20">
        {/* Brand Header */}
        <div className="h-16 px-5 border-b border-slate-800/80 flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-xs">
            <HardHat className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-base tracking-tight text-white">InfraScan</span>
              <span className="text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.2 rounded">
                AI
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Civil Structural Intelligence</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-5 space-y-1 overflow-y-auto">
          <p className="px-3 text-[10px] font-bold tracking-wider uppercase text-slate-400 mb-2">
            Platform Menu
          </p>
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-blue-600 text-white font-semibold shadow-xs'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* User Card & Logout */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/30">
          <div className="flex items-center gap-2.5 p-2 rounded-xl bg-slate-800/50 border border-slate-800 mb-2">
            <div className="h-8 w-8 rounded-lg bg-blue-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
              <p className="text-[10px] text-blue-400 font-medium truncate">{user?.role?.name || 'User'}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ── Main Content Container ───────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-slate-200/80 px-4 sm:px-8 flex items-center justify-between sticky top-0 z-10 shadow-xs">
          <div className="flex items-center gap-3">
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
              aria-label="Toggle navigation"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="font-bold text-slate-900 text-sm sm:text-base tracking-tight truncate">
              {getPageTitle()}
            </h1>
          </div>

          {/* AI Status & Notification Center */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Live Model Status Pill */}
            <div className="hidden sm:inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>AI Engine Active • 94.6%</span>
            </div>

            <div className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
              <Cpu className="w-3.5 h-3.5 text-slate-500" />
              <span>ONNX CPU 48ms</span>
            </div>

            {/* Notification Bell Dropdown */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setShowNotifMenu(!showNotifMenu)}
                className="relative p-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors"
                title="Notifications & Safety Alerts"
                aria-label="Notifications"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifMenu && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-2xl shadow-xl border border-slate-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-1">
                  <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Bell className="w-4 h-4 text-blue-600" />
                      <span className="text-xs font-bold text-slate-900">Alerts & Notifications</span>
                      {unreadCount > 0 && (
                        <span className="text-[10px] font-semibold bg-rose-100 text-rose-700 px-1.5 py-0.2 rounded-full">
                          {unreadCount} unread
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="text-[11px] text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                    {notifications.length === 0 ? (
                      <div className="p-6 text-center text-xs text-slate-400">
                        No alerts or notifications at this time.
                      </div>
                    ) : (
                      notifications.map(n => {
                        const isCritical = n.alert_level === 'Critical';
                        const isHigh = n.alert_level === 'High';
                        return (
                          <div
                            key={n.id}
                            onClick={() => handleNotificationClick(n)}
                            className={`p-3 text-xs cursor-pointer hover:bg-slate-50 transition-colors flex items-start gap-2.5 ${
                              !n.is_read ? 'bg-blue-50/50' : ''
                            }`}
                          >
                            <div className="mt-0.5 shrink-0">
                              {isCritical ? (
                                <ShieldAlert className="w-4 h-4 text-rose-600" />
                              ) : isHigh ? (
                                <AlertTriangle className="w-4 h-4 text-amber-600" />
                              ) : (
                                <Info className="w-4 h-4 text-blue-600" />
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-1 mb-0.5">
                                <span className="font-semibold text-slate-900 truncate">{n.title}</span>
                                <span className={`text-[9px] px-1.5 py-0.2 rounded-full font-bold ${
                                  isCritical ? 'bg-rose-100 text-rose-700' :
                                  isHigh ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'
                                }`}>
                                  {n.alert_level}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">{n.message}</p>
                              <span className="text-[10px] text-slate-400 mt-1 block">
                                {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden bg-slate-900 border-b border-slate-800 p-4 space-y-1">
            {navLinks.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium ${
                      isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium text-rose-400 hover:bg-slate-800 rounded-lg mt-2 pt-2 border-t border-slate-800"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
        )}

        {/* Page Content Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto bg-slate-50">
          <Outlet />
        </main>

        {/* Clean Minimalist Footer */}
        <footer className="bg-white border-t border-slate-200/80 px-4 sm:px-8 py-2.5 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-2 text-slate-600">
            <span className="font-semibold text-slate-800">InfraScan AI</span>
            <span>•</span>
            <span>Civil Infrastructure Health & Damage Assessment</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Decision support tool — Certified structural inspections require a licensed professional engineer
          </p>
        </footer>
      </div>
    </div>
  );
};
