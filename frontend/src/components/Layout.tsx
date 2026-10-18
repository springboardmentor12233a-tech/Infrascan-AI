import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Building2, 
  ClipboardCheck, 
  Users, 
  LayoutDashboard, 
  LogOut, 
  AlertTriangle,
  HardHat
} from 'lucide-react';

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isAdmin = user?.role?.name === 'Administrator';

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900">
      {/* Top Disclaimer Banner */}
      <div className="bg-amber-500 text-slate-900 px-4 py-1.5 text-xs font-medium text-center flex items-center justify-center gap-2 border-b border-amber-600 shadow-sm">
        <AlertTriangle className="w-4 h-4 text-slate-900 flex-shrink-0" />
        <span>
          <strong>Decision Support Notice:</strong> AI results are decision support, not a structural safety evaluation. Always consult a certified professional engineer.
        </span>
      </div>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col shadow-lg">
          <div className="p-5 border-b border-slate-800 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md">
              <HardHat className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg leading-tight tracking-wide text-white">InfraScan</h1>
              <p className="text-xs text-slate-400">Civil Asset Assessment</p>
            </div>
          </div>

          {/* User Brief */}
          <div className="px-5 py-4 border-b border-slate-800 bg-slate-950/40">
            <p className="text-sm font-semibold text-white truncate">{user?.full_name}</p>
            <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            <div className="mt-2 inline-block px-2 py-0.5 text-[11px] font-medium bg-blue-900/60 text-blue-300 rounded border border-blue-700/50">
              {user?.role?.name || 'User'}
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </NavLink>

            <NavLink
              to="/assets"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Building2 className="w-4 h-4" />
              <span>Infrastructure Assets</span>
            </NavLink>

            {isAdmin && (
              <NavLink
                to="/admin/users"
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <Users className="w-4 h-4" />
                <span>User Management</span>
              </NavLink>
            )}
          </nav>

          {/* Logout */}
          <div className="p-4 border-t border-slate-800">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-3 py-2 text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-slate-800/60 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-8 overflow-y-auto max-h-[calc(100vh-32px)]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
