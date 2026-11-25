import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { notificationsApi } from "../api/client";
import rolePermissions from "../config/role_permissions.json";
import { useLiveEvents } from "../hooks/useLiveEvents";
import { LiveStatusChip } from "./LiveStatusChip";

const roleBadgeColors: Record<string, string> = {
  admin: "bg-purple-900/80 text-purple-200 border-purple-700",
  manager: "bg-emerald-900/80 text-emerald-200 border-emerald-700",
  civil_engineer: "bg-blue-900/80 text-blue-200 border-blue-700",
  inspector: "bg-amber-900/80 text-amber-200 border-amber-700",
  maintenance_engineer: "bg-indigo-900/80 text-indigo-200 border-indigo-700",
};

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const role = user?.role || "inspector";
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  const { status: liveStatus } = useLiveEvents((event) => {
    if (event.type === 'notification.created') {
      setUnreadCount((c) => c + 1);
    }
  });

  const fetchUnread = async () => {
    if (!user) return;
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.unread_count);
    } catch {
      // Ignore polling errors in background
    }
  };

  useEffect(() => {
    fetchUnread();
    const timer = setInterval(fetchUnread, 30000);
    return () => clearInterval(timer);
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(`${path}/`);

  // Filter routes allowed for current role based on single shared role_permissions.json
  const allowedNavRoutes = Object.entries(rolePermissions.routes)
    .filter(([_, cfg]) => cfg.roles.includes(role))
    .filter(([path]) => !["/profile", "/notifications"].includes(path));

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

            {/* Desktop Navigation Links - Role Governed */}
            <nav className="hidden md:flex space-x-1.5" aria-label="Main Navigation">
              {allowedNavRoutes.map(([path, cfg]) => (
                <Link
                  key={path}
                  to={path}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive(path)
                      ? "bg-slate-800 text-indigo-400"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  {cfg.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Right Controls: Notifications, User Badge, Logout, Hamburger */}
          <div className="flex items-center space-x-3">
            {user && <LiveStatusChip status={liveStatus} />}
            {user && (
              <Link
                to="/notifications"
                className="relative p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-full transition"
                title="Notifications"
                aria-label={`Notifications, ${unreadCount} unread`}
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                {unreadCount > 0 && (
                  <span className="absolute top-0.5 right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Link>
            )}

            {user && (
              <div className="hidden sm:flex items-center space-x-2 text-right">
                <Link to="/profile" className="hover:opacity-80 transition" aria-label="User profile">
                  <p className="text-xs font-medium text-slate-100">{user.full_name}</p>
                  <span
                    className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded border uppercase tracking-wider ${
                      roleBadgeColors[role] || "bg-slate-800 text-slate-300 border-slate-700"
                    }`}
                  >
                    {role.replace("_", " ")}
                  </span>
                </Link>
              </div>
            )}

            <button
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-md text-sm font-medium text-slate-300 hover:bg-rose-900/60 hover:text-rose-200 transition-colors border border-slate-700 hover:border-rose-800"
            >
              Logout
            </button>

            {/* Mobile menu toggle */}
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition"
              aria-label="Toggle navigation menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isMobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Navigation - Role Governed */}
        {isMobileMenuOpen && (
          <nav className="md:hidden bg-slate-800 border-t border-slate-700 px-2 pt-2 pb-4 space-y-1">
            {allowedNavRoutes.map(([path, cfg]) => (
              <Link
                key={path}
                to={path}
                className="block px-3 py-2 rounded text-sm text-slate-200 hover:bg-slate-700"
              >
                {cfg.label}
              </Link>
            ))}
            {user && (
              <div className="pt-2 border-t border-slate-700 mt-2 px-3">
                <span
                  className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded border uppercase tracking-wider ${
                    roleBadgeColors[role] || "bg-slate-800 text-slate-300 border-slate-700"
                  }`}
                >
                  {role.replace("_", " ")}
                </span>
                <p className="text-xs text-slate-400 mt-1">{user.full_name}</p>
                <button
                  onClick={handleLogout}
                  className="mt-3 w-full text-left text-sm text-rose-300 hover:text-rose-200 py-1"
                >
                  Logout
                </button>
              </div>
            )}
          </nav>
        )}
      </div>
    </header>
  );
};

