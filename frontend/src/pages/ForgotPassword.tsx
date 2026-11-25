import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/client'

export const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await authApi.forgotPassword(email)
      setMessage(res.message)
      setSubmitted(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit request. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 mb-2">
            <span className="font-black text-xl tracking-tight text-indigo-600">INFRASCAN</span>
          </div>
          <h1 className="text-xl font-bold text-slate-800">Forgot Password</h1>
          <p className="text-xs text-slate-500 mt-1">
            Enter your account email to receive a password reset token.
          </p>
        </div>

        {submitted ? (
          <div className="text-center space-y-4">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm">
              {message}
            </div>
            <p className="text-xs text-slate-500">
              In development mode, the reset token is output to the server console.
            </p>
            <div className="pt-2 flex flex-col gap-2">
              <Link
                to="/reset-password"
                className="w-full inline-flex justify-center items-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition"
              >
                Proceed to Reset Password
              </Link>
              <Link
                to="/login"
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Back to Sign In
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs font-medium">
                {error}
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="inspector@agency.gov"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold shadow-sm transition"
            >
              {loading ? 'Submitting...' : 'Send Reset Instructions'}
            </button>

            <div className="text-center pt-2">
              <Link
                to="/login"
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default ForgotPassword
