import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, ShieldAlert, ArrowLeft, CheckCircle2, AlertTriangle } from 'lucide-react'
import { authService } from '@/services/authService'
import { useAppStore } from '@/store/useAppStore'
import { USER_ROLES, API_CONFIG } from '@/lib/constants'

const loginSchema = z.object({
  email: z.string().email('Enter a valid engineering email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

const registerSchema = z.object({
  name: z.string().min(2, 'Full name is required'),
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  role: z.string().min(1, 'Select a role'),
  department: z.string().min(2, 'Department is required'),
})

const forgotSchema = z.object({
  email: z.string().email('Enter a valid email address'),
})

function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="flex items-center justify-center gap-2.5 mb-6">
          <div className="w-9 h-9 rounded-md bg-[#0F2942] flex items-center justify-center text-white">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
          </div>
          <span className="text-lg font-bold text-slate-900 tracking-tight">InfraScan</span>
        </Link>
        <div className="bg-white py-8 px-6 sm:px-8 shadow-sm rounded-lg border border-slate-200">
          <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
          <p className="text-xs text-slate-500 mt-1 mb-6">{subtitle}</p>
          {children}
        </div>
        <p className="mt-4 text-center text-[11px] text-slate-400">
          {API_CONFIG.enableMockData
            ? 'Demo mode · Any credentials accepted'
            : 'Live API mode · Connected to FastAPI backend'}
        </p>
      </div>
    </div>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setCurrentUser = useAppStore((s) => s.setCurrentUser)
  const setAuthenticated = useAppStore((s) => s.setAuthenticated)
  const isAuthenticated = useAppStore((s) => s.isAuthenticated)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/app/dashboard'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, location.state])

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: 'elena.vance@infrascan.io', password: 'password123' },
  })

  const onSubmit = async (values: z.infer<typeof loginSchema>) => {
    try {
      setError('')
      const res = await authService.login(values)
      setCurrentUser(res.user)
      setAuthenticated(true)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/app/dashboard'
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Please verify your credentials.')
    }
  }

  return (
    <AuthLayout title="Sign in to InfraScan" subtitle="Access your infrastructure inspection workspace">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {error && (
          <div className="p-2.5 text-xs bg-red-50 text-red-700 border border-red-200 rounded flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Work Email</label>
          <input
            type="email"
            {...register('email')}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-600/20 focus:border-cyan-600"
          />
          {errors.email && <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>}
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-medium text-slate-700">Password</label>
            <Link to="/forgot-password" className="text-xs text-cyan-700 hover:underline">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              {...register('password')}
              className="w-full px-3 py-2 pr-10 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-600/20 focus:border-cyan-600"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
              aria-label="Toggle password visibility"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.password && <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 px-4 bg-[#0F2942] hover:bg-[#163859] text-white text-sm font-semibold rounded-md transition-colors disabled:opacity-60"
        >
          {isSubmitting ? 'Signing in…' : 'Sign In'}
        </button>
      </form>
      <p className="mt-5 text-center text-xs text-slate-600">
        Need an account?{' '}
        <Link to="/register" className="text-cyan-700 font-medium hover:underline">
          Register organization user
        </Link>
      </p>
    </AuthLayout>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const setCurrentUser = useAppStore((s) => s.setCurrentUser)
  const setAuthenticated = useAppStore((s) => s.setAuthenticated)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: 'Civil Engineer', department: 'Structural Bridges Division' },
  })

  const onSubmit = async (values: z.infer<typeof registerSchema>) => {
    try {
      setError('')
      const res = await authService.register(values)
      setCurrentUser(res.user)
      setAuthenticated(true)
      navigate('/app/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.')
    }
  }

  return (
    <AuthLayout title="Create InfraScan Account" subtitle="Register as an engineer, inspector, or manager">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
        {error && (
          <div className="p-2.5 text-xs bg-red-50 text-red-700 border border-red-200 rounded flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Full Name</label>
          <input
            type="text"
            {...register('name')}
            placeholder="Elena Vance, PE"
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:border-cyan-600"
          />
          {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Work Email</label>
          <input
            type="email"
            {...register('email')}
            placeholder="name@company.com"
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:border-cyan-600"
          />
          {errors.email && <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Role</label>
            <select
              {...register('role')}
              className="w-full px-2.5 py-2 text-sm border border-slate-300 rounded-md bg-white focus:outline-none focus:border-cyan-600"
            >
              {USER_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Department</label>
            <input
              type="text"
              {...register('department')}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:border-cyan-600"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Password</label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              {...register('password')}
              className="w-full px-3 py-2 pr-10 text-sm border border-slate-300 rounded-md focus:outline-none focus:border-cyan-600"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2.5 top-2.5 text-slate-400"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.password && <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 px-4 bg-[#0F2942] hover:bg-[#163859] text-white text-sm font-semibold rounded-md transition-colors disabled:opacity-60"
        >
          {isSubmitting ? 'Creating account…' : 'Create Account'}
        </button>
      </form>
      <p className="mt-5 text-center text-xs text-slate-600">
        Already registered?{' '}
        <Link to="/login" className="text-cyan-700 font-medium hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}

export function ForgotPasswordPage() {
  const [sentMessage, setSentMessage] = useState('')
  const [error, setError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof forgotSchema>>({
    resolver: zodResolver(forgotSchema),
  })

  const onSubmit = async (values: z.infer<typeof forgotSchema>) => {
    try {
      setError('')
      const res = await authService.requestPasswordReset(values.email)
      setSentMessage(res.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email.')
    }
  }

  return (
    <AuthLayout title="Reset Password" subtitle="Enter your work email to receive reset instructions">
      {sentMessage ? (
        <div className="p-4 rounded-md bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Reset Request Sent</p>
            <p className="mt-1">{sentMessage}</p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="p-2.5 text-xs bg-red-50 text-red-700 border border-red-200 rounded">{error}</div>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Work Email</label>
            <input
              type="email"
              {...register('email')}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:border-cyan-600"
            />
            {errors.email && <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>}
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 bg-[#0F2942] hover:bg-[#163859] text-white text-sm font-semibold rounded-md transition-colors disabled:opacity-60"
          >
            {isSubmitting ? 'Sending…' : 'Send Reset Link'}
          </button>
        </form>
      )}
      <Link to="/login" className="mt-5 inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Sign In
      </Link>
    </AuthLayout>
  )
}
