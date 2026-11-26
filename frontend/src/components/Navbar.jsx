import React, { useState, useEffect } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, LogOut, User, Lock, Upload } from 'lucide-react';

export default function Navbar() {
  const [health, setHealth] = useState({ status: 'checking' });
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(() => setHealth({ status: 'offline' }));
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Nav items based on role
  let navItems = [];
  if (isAuthenticated) {
    if (isAdmin) {
      navItems = [
        { name: 'Admin Dashboard', path: '/admin/dashboard' },
        { name: 'All Inspections', path: '/inspections' },
        { name: 'Assets', path: '/assets' },
        { name: 'Damage Map', path: '/map' },
        { name: 'Model Evaluation', path: '/models' },
      ];
    } else {
      navItems = [
        { name: 'User Dashboard', path: '/user/dashboard' },
        { name: 'New Inspection', path: '/new-inspection' },
        { name: 'My Inspections', path: '/inspections' },
        { name: 'Assets', path: '/assets' },
        { name: 'Damage Map', path: '/map' },
      ];
    }
  }

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <Link
              to={isAuthenticated ? (isAdmin ? '/admin/dashboard' : '/user/dashboard') : '/login'}
              className="flex items-center gap-3 text-xl font-bold tracking-tight text-white hover:opacity-90 transition"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white font-black text-lg">
                IS
              </div>
              <div className="flex flex-col">
                <span className="flex items-center gap-1.5 font-bold">
                  InfraScan
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/30">
                    AI 2.0
                  </span>
                </span>
                <span className="text-[10px] text-slate-400 font-medium tracking-normal">
                  Civil Damage Intelligence
                </span>
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map(item => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`
                }
              >
                {item.name}
              </NavLink>
            ))}
          </nav>

          {/* Right Section: Status, User Pill, Action */}
          <div className="flex items-center gap-3">
            {/* Backend Health Pill */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  health.status === 'online' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              ></span>
              <span className="text-slate-300 font-medium text-[11px]">
                Backend {health.status === 'online' ? 'Active' : 'Offline'}
              </span>
            </div>

            {isAuthenticated ? (
              <div className="flex items-center gap-2.5">
                {/* User Role Badge */}
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-xs">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isAdmin ? 'bg-amber-400' : 'bg-blue-400'
                    }`}
                  ></div>
                  <span className="text-white font-semibold">{user?.username}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-black uppercase tracking-wider ${
                      isAdmin
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-blue-500/20 text-blue-300'
                    }`}
                  >
                    {user?.role}
                  </span>
                </div>

                <Link
                  to="/new-inspection"
                  className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-md shadow-blue-600/30 transition flex items-center gap-1.5"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">New Inspection</span>
                </Link>

                <button
                  onClick={handleLogout}
                  title="Log Out"
                  className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 transition"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white shadow-md shadow-blue-600/30 transition"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
