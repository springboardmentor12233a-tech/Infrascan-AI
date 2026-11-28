import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import { HardHat, Lock, Mail, AlertCircle, ArrowRight, ShieldCheck, Sparkles, CheckCircle2 } from 'lucide-react';
import { AuthResponse } from '../types';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLoginSubmit = async (loginEmail?: string, loginPassword?: string) => {
    const finalEmail = loginEmail || email;
    const finalPass = loginPassword || password;

    setError('');
    setLoading(true);

    try {
      const params = new URLSearchParams();
      params.append('username', finalEmail);
      params.append('password', finalPass);

      const res = await api.post<AuthResponse>('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      login(res.data.access_token, res.data.user);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLoginSubmit();
  };

  const handleQuickDemo = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('Password123!');
    handleLoginSubmit(demoEmail, 'Password123!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden font-sans">
      {/* Background Ambient Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-brand-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-[400px] h-[300px] bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none" />

      {/* Main Card */}
      <div className="max-w-md w-full bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-white/20 relative z-10 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="h-14 w-14 bg-gradient-to-tr from-brand-600 to-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-brand-500/25 mx-auto mb-3">
            <HardHat className="w-7 h-7" />
          </div>
          <div className="flex items-center justify-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">InfraScan</h1>
            <span className="text-[11px] font-bold bg-brand-50 text-brand-700 border border-brand-200 px-2 py-0.5 rounded-full">
              AI
            </span>
          </div>
          <p className="text-xs text-slate-500 font-medium">
            AI-Assisted Structural Health & Concrete Crack Assessment
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* 1-Click Demo Login Shortcuts */}
        <div className="space-y-2 p-3 rounded-2xl bg-slate-50 border border-slate-100">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-brand-600" />
            <span>1-Click Demo Access</span>
          </p>
          <div className="grid grid-cols-3 gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => handleQuickDemo('admin@infrascan.com')}
              className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-brand-500 hover:text-brand-600 font-semibold text-[11px] transition-all shadow-xs"
            >
              Admin
            </button>
            <button
              type="button"
              onClick={() => handleQuickDemo('manager@infrascan.com')}
              className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-brand-500 hover:text-brand-600 font-semibold text-[11px] transition-all shadow-xs"
            >
              Manager
            </button>
            <button
              type="button"
              onClick={() => handleQuickDemo('inspector@infrascan.com')}
              className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-brand-500 hover:text-brand-600 font-semibold text-[11px] transition-all shadow-xs"
            >
              Inspector
            </button>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              Work Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="inspector@infrascan.com"
                className="input-field pl-10"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-field pl-10"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary py-2.5 font-bold text-sm shadow-md flex items-center justify-center gap-2 mt-2"
          >
            <span>{loading ? 'Authenticating...' : 'Sign In to Workspace'}</span>
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="pt-2 border-t border-slate-100 text-center">
          <p className="text-xs text-slate-500">
            Need an account?{' '}
            <Link to="/register" className="text-brand-600 font-semibold hover:underline">
              Create an inspection account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
