import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export const Register: React.FC = () => {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState<'inspector' | 'admin'>('inspector')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }

    setLoading(true)
    try {
      await register(fullName, email, password, selectedRole)
      navigate('/dashboard')
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        const detail = err.response.data.detail
        if (typeof detail === 'string') {
          setError(detail)
        } else if (Array.isArray(detail)) {
          setError(detail.map((d: any) => d.msg || JSON.stringify(d)).join(', '))
        } else {
          setError(JSON.stringify(detail))
        }
      } else {
        setError(err.message || 'Registration failed. Please check the details and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#141619] text-white flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-[#0A21C0]/15 rounded-full blur-[130px] pointer-events-none" />

      <div className="max-w-md w-full bg-[#2C2E3A] border border-[rgba(179,180,189,0.18)] rounded-3xl p-8 shadow-2xl relative z-10 backdrop-blur-xl">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-[#0A21C0] shadow-[0_0_20px_rgba(10,33,192,0.6)] mb-4 font-black text-xl text-white">
            IS
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Infra<span className="text-[#0A21C0]">Scan</span>
          </h1>
          <p className="text-sm text-[#B3B4BD] mt-2">
            Create an inspector account for automated damage workflows
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-3.5 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-200 text-sm">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#B3B4BD] uppercase tracking-wider mb-1.5">
              Full Name
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Morgan"
              className="w-full px-4 py-2.5 bg-[#141619]/80 border border-[rgba(179,180,189,0.2)] rounded-xl text-white text-sm focus:outline-none focus:border-[#0A21C0] focus:ring-1 focus:ring-[#0A21C0] transition-colors placeholder:text-gray-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#B3B4BD] uppercase tracking-wider mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full px-4 py-2.5 bg-[#141619]/80 border border-[rgba(179,180,189,0.2)] rounded-xl text-white text-sm focus:outline-none focus:border-[#0A21C0] focus:ring-1 focus:ring-[#0A21C0] transition-colors placeholder:text-gray-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#B3B4BD] uppercase tracking-wider mb-1.5">
              Password (min 8 characters)
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-2.5 bg-[#141619]/80 border border-[rgba(179,180,189,0.2)] rounded-xl text-white text-sm focus:outline-none focus:border-[#0A21C0] focus:ring-1 focus:ring-[#0A21C0] transition-colors placeholder:text-gray-500"
            />
          </div>

          {/* Account Role Selection */}
          <div>
            <label className="block text-xs font-semibold text-[#B3B4BD] uppercase tracking-wider mb-2">
              Select User Role / Account Type
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSelectedRole('inspector')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  selectedRole === 'inspector'
                    ? 'bg-[#0A21C0]/20 border-[#0A21C0] shadow-[0_0_15px_rgba(10,33,192,0.3)]'
                    : 'bg-[#141619]/60 border-[rgba(179,180,189,0.15)] hover:border-[rgba(179,180,189,0.3)]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    Inspector
                  </span>
                  {selectedRole === 'inspector' && (
                    <span className="text-[#0A21C0] text-xs font-bold">✓</span>
                  )}
                </div>
                <p className="text-[11px] text-[#B3B4BD] leading-tight">
                  Field inspection, image capture & crack upload.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setSelectedRole('admin')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  selectedRole === 'admin'
                    ? 'bg-[#0A21C0]/20 border-[#0A21C0] shadow-[0_0_15px_rgba(10,33,192,0.3)]'
                    : 'bg-[#141619]/60 border-[rgba(179,180,189,0.15)] hover:border-[rgba(179,180,189,0.3)]'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
                    Administrator
                  </span>
                  {selectedRole === 'admin' && (
                    <span className="text-[#0A21C0] text-xs font-bold">✓</span>
                  )}
                </div>
                <p className="text-[11px] text-[#B3B4BD] leading-tight">
                  Asset management, reports & overall governance.
                </p>
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-6 bg-[#0A21C0] hover:bg-[#1631E0] text-white font-semibold rounded-full shadow-[0_4px_25px_rgba(10,33,192,0.45)] transition-all text-sm disabled:opacity-50 mt-2 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Creating Account...</span>
              </>
            ) : (
              `Create ${selectedRole === 'admin' ? 'Administrator' : 'Inspector'} Account`
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="mt-6 text-center text-xs text-[#B3B4BD]">
          Already have an account?{' '}
          <Link
            to="/login"
            className="text-[#0A21C0] hover:underline font-semibold ml-1"
          >
            Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
