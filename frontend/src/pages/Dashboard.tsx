import React, { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import { dashboardApi } from '../api/client'

interface AttentionItem {
  id: string
  category: string
  title: string
  description: string
  severity: string
  link: string
  created_at: string | null
}

export const Dashboard: React.FC = () => {
  const { user } = useAuth()
  const [attentionItems, setAttentionItems] = useState<AttentionItem[]>([])
  const [loadingAttention, setLoadingAttention] = useState<boolean>(true)

  const loadAttention = useCallback(async () => {
    try {
      setLoadingAttention(true)
      const data = await dashboardApi.getAttention()
      setAttentionItems(data.items || [])
    } catch {
      // Non-critical, fallback to empty array
      setAttentionItems([])
    } finally {
      setLoadingAttention(false)
    }
  }, [])

  useEffect(() => {
    loadAttention()
  }, [loadAttention])

  // Listen for real-time events to refresh attention feed automatically
  useEffect(() => {
    const handleLiveEvent = () => {
      loadAttention()
    }
    window.addEventListener('infrascan:event', handleLiveEvent)
    return () => window.removeEventListener('infrascan:event', handleLiveEvent)
  }, [loadAttention])

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">CRITICAL</span>
      case 'high':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">HIGH</span>
      case 'medium':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-100 text-yellow-800 border border-yellow-300">MEDIUM</span>
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-300">INFO</span>
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Banner */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8 mb-6">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-800 tracking-tight">
            Welcome, {user?.full_name}{' '}
            <span className="text-indigo-600 font-medium text-xl md:text-2xl">
              ({user?.role.replace('_', ' ')})
            </span>
          </h1>
          <p className="text-sm text-slate-500 mt-2">
            InfraScan AI-Powered Crack &amp; Damage Assessment for Civil Infrastructure.
          </p>
        </div>

        {/* Needs Your Attention Section */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 pb-3 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-slate-800 tracking-tight">
                Needs your attention
              </h2>
              {attentionItems.length > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">
                  {attentionItems.length}
                </span>
              )}
            </div>
            <span className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded font-medium mt-2 sm:mt-0">
              AI result for engineer review, not a final structural safety verdict.
            </span>
          </div>

          {loadingAttention ? (
            <div className="py-8 text-center text-slate-400 text-sm">
              <div className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-indigo-600 border-t-transparent mb-2" />
              <p>Checking live attention feed...</p>
            </div>
          ) : attentionItems.length === 0 ? (
            <div className="py-6 text-center text-slate-500">
              <p className="text-sm font-semibold text-slate-700">No items require your attention right now.</p>
              <p className="text-xs text-slate-400 mt-1">
                No damage detected by the AI. This is not evidence that there is no damage.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
              {attentionItems.map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-sm transition bg-slate-50/50 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                        {item.category.replace('_', ' ')}
                      </span>
                      {getSeverityBadge(item.severity)}
                    </div>
                    <h3 className="text-sm font-bold text-slate-800">{item.title}</h3>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-200/60 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}
                    </span>
                    <Link
                      to={item.link}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition flex items-center space-x-1"
                    >
                      <span>Take Action</span>
                      <span>&rarr;</span>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Account Details Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Your Account Details
            </h2>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-400 block text-xs">Email</span>
                <span className="font-medium text-slate-700">{user?.email}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Role</span>
                <span className="inline-block px-2 py-0.5 text-xs font-semibold rounded bg-indigo-50 text-indigo-700 uppercase">
                  {user?.role.replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Status</span>
                <span className="inline-flex items-center text-xs font-medium text-emerald-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span>
                  Active
                </span>
              </div>
            </div>
            <div className="mt-5 pt-4 border-t border-slate-100">
              <Link
                to="/profile"
                className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
              >
                Edit Profile or Change Password &rarr;
              </Link>
            </div>
          </div>

          {/* Role Scope Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Assigned Permissions
            </h2>
            <p className="text-xs text-slate-500 mb-3">
              Your capabilities in InfraScan are scoped by your role:
            </p>
            <ul className="text-xs text-slate-600 space-y-2 list-disc pl-4">
              {user?.role === 'admin' ? (
                <>
                  <li>Full system administration and user governance</li>
                  <li>Monitor asynchronous background jobs &amp; models</li>
                  <li>Review audit trails and server health status</li>
                </>
              ) : user?.role === 'civil_engineer' ? (
                <>
                  <li>Review provisional AI severity and priority assessments</li>
                  <li>Verify completed maintenance repair tasks</li>
                  <li>Generate official inspection reports &amp; exports</li>
                </>
              ) : user?.role === 'manager' ? (
                <>
                  <li>Schedule inspections and assign to field inspectors</li>
                  <li>Create and manage infrastructure assets</li>
                  <li>Monitor portfolio damage statistics and reports</li>
                </>
              ) : user?.role === 'maintenance_engineer' ? (
                <>
                  <li>View assigned repair work orders</li>
                  <li>Update task execution status (in-progress, completed)</li>
                  <li>Record repair resolution notes and field observations</li>
                </>
              ) : (
                <>
                  <li>Execute assigned field inspections</li>
                  <li>Upload concrete and pavement defect imagery</li>
                  <li>Monitor real-time AI analysis progress</li>
                </>
              )}
            </ul>
            {user?.role === 'admin' && (
              <div className="mt-5 pt-4 border-t border-slate-100">
                <Link
                  to="/users"
                  className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                >
                  Manage Users &amp; Roles &rarr;
                </Link>
              </div>
            )}
          </div>

          {/* Quick Stats / System Status */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Operational Hub
            </h2>
            <p className="text-xs text-slate-500 mb-4">
              Connected to real-time events engine over PostgreSQL LISTEN/NOTIFY.
            </p>
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center space-x-2 mb-3">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-xs font-semibold text-emerald-800">
                Live Real-Time Engine Active
              </span>
            </div>
            <div className="space-y-2 pt-2 border-t border-slate-100 text-xs font-semibold text-indigo-600">
              <div>
                <Link to="/upload" className="hover:underline flex items-center space-x-1 text-indigo-700 font-bold">
                  <span>⬆️</span>
                  <span>Upload Field Photos & Run AI Analysis &rarr;</span>
                </Link>
              </div>
              <div>
                <Link to="/map" className="hover:underline">
                  Interactive GIS Damage Map &rarr;
                </Link>
              </div>
              {['admin', 'manager', 'civil_engineer', 'maintenance_engineer'].includes(user?.role || '') && (
                <div>
                  <Link to="/maintenance" className="hover:underline">
                    Maintenance Work Orders &rarr;
                  </Link>
                </div>
              )}
              {['admin', 'manager', 'civil_engineer'].includes(user?.role || '') && (
                <div>
                  <Link to="/reports" className="hover:underline">
                    Inspection Reports &amp; Analytics &rarr;
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
export default Dashboard
