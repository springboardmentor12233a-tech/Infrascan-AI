import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, User, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const loggedUser = await login(username, password);
      if (loggedUser.role === 'admin') {
        navigate('/admin/dashboard', { replace: true });
      } else {
        navigate('/user/dashboard', { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (u, p) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Brand Card */}
        <div className="text-center mb-8">
          <div className="inline-flex w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 items-center justify-center shadow-xl shadow-blue-500/25 mb-4">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">InfraScan Portal</h1>
          <p className="text-sm text-slate-400 mt-2">
            AI-Powered Civil Infrastructure Crack & Damage Intelligence
          </p>
        </div>

        <div className="glass-card p-8 rounded-2xl border border-slate-800 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>

          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Lock className="w-5 h-5 text-blue-400" />
            Account Authentication
          </h2>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Username or Email
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username or email"
                  className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                />
                <User className="w-4 h-4 text-slate-500 absolute right-3.5 top-3.5 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                />
                <Lock className="w-4 h-4 text-slate-500 absolute right-3.5 top-3.5 pointer-events-none" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-bold tracking-wide shadow-lg shadow-blue-500/25 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Authenticating...
                </>
              ) : (
                'Sign In to Dashboard'
              )}
            </button>
          </form>

          {/* Registration helper */}
          <div className="mt-8 pt-6 border-t border-slate-800/80 text-xs text-slate-400">
            <span className="font-semibold text-slate-300 block mb-2">First time accessing InfraScan?</span>
            <Link
              to="/register"
              className="p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 flex items-center justify-between text-left transition"
            >
              <div>
                <div className="font-bold text-blue-400">Create Inspector Account</div>
                <div className="text-[10px] text-slate-400">Register new personal account to start inspecting</div>
              </div>
              <span className="text-blue-400 text-sm font-bold">&rarr;</span>
            </Link>
          </div>
        </div>

        <div className="text-center mt-6 text-xs text-slate-500">
          Need an account?{' '}
          <Link to="/register" className="text-blue-400 hover:underline font-semibold">
            Register as a New Inspector
          </Link>
        </div>
      </div>
    </div>
  );
}
