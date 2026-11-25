import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import {
  notificationsApi,
  type NotificationItem,
  type NotificationPreference,
} from '../api/client'
import { useAuth } from '../context/AuthContext'

export const Notifications: React.FC = () => {
  const { role } = useAuth()
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Filters & Pagination
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [total, setTotal] = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)

  // Preferences Modal
  const [isPrefOpen, setIsPrefOpen] = useState(false)
  const [pref, setPref] = useState<NotificationPreference | null>(null)
  const [prefLoading, setPrefLoading] = useState(false)
  const [isSavingPref, setIsSavingPref] = useState(false)

  // Sweep
  const [isSweeping, setIsSweeping] = useState(false)

  const loadNotifications = async () => {
    try {
      setLoading(true)
      const data = await notificationsApi.listNotifications({
        unread_only: unreadOnly,
        page,
        page_size: pageSize,
      })
      setNotifications(data.items)
      setTotal(data.total)
      setUnreadCount(data.unread_count)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotifications()
  }, [unreadOnly, page])

  const handleMarkRead = async (id: number) => {
    try {
      await notificationsApi.markRead(id)
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      )
      setUnreadCount(c => Math.max(0, c - 1))
    } catch (err: any) {
      setError('Could not mark notification as read')
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead()
      setNotifications(prev =>
        prev.map(n => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
      )
      setUnreadCount(0)
      setSuccessMsg('All notifications marked as read.')
    } catch (err: any) {
      setError('Could not mark all as read')
    }
  }

  const openPreferencesModal = async () => {
    setIsPrefOpen(true)
    setError(null)
    try {
      setPrefLoading(true)
      const p = await notificationsApi.getPreferences()
      setPref(p)
    } catch (err: any) {
      setError('Could not load preferences')
    } finally {
      setPrefLoading(false)
    }
  }

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!pref) return
    try {
      setIsSavingPref(true)
      const updated = await notificationsApi.updatePreferences({
        in_app_enabled: pref.in_app_enabled,
        email_enabled: pref.email_enabled,
        min_severity: pref.min_severity,
      })
      setPref(updated)
      setIsPrefOpen(false)
      setSuccessMsg('Notification preferences updated successfully.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update preferences')
    } finally {
      setIsSavingPref(false)
    }
  }

  const handleTriggerSweep = async () => {
    try {
      setIsSweeping(true)
      const res = await notificationsApi.triggerSweep()
      setSuccessMsg(
        `Sweep completed: ${res.maintenance_alerts} maintenance alerts & ${res.overdue_inspections} overdue inspection reminders dispatched.`
      )
      loadNotifications()
    } catch (err: any) {
      setError('Failed to trigger deadline sweep')
    } finally {
      setIsSweeping(false)
    }
  }

  const getEntityLink = (notif: NotificationItem) => {
    if (!notif.entity_type || !notif.entity_id) return null
    if (notif.entity_type === 'inspection') return `/inspections/${notif.entity_id}`
    if (notif.entity_type === 'asset') return `/assets/${notif.entity_id}`
    if (notif.entity_type === 'report') return `/reports`
    return null
  }

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'critical_alert':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 uppercase">Critical Alert</span>
      case 'damage_detected':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 uppercase">Damage</span>
      case 'maintenance_deadline_approaching':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-orange-100 text-orange-800 uppercase">Deadline</span>
      case 'inspection_assigned':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800 uppercase">Assignment</span>
      case 'inspection_completed':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 uppercase">Completed</span>
      case 'report_generated':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-100 text-purple-800 uppercase">Report</span>
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 uppercase">{type.replace('_', ' ')}</span>
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <Navbar />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Mandatory Header Disclaimer Alert */}
        <div className="mb-6 p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r shadow-sm flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div>
            <h4 className="text-sm font-semibold text-amber-800">Mandatory Engineering Disclaimer</h4>
            <p className="text-xs text-amber-700 mt-0.5">
              AI result for engineer review, not a final structural safety verdict. Alerts indicate model findings that require qualified engineering verification.
            </p>
          </div>
        </div>

        {/* Action Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900">Notifications &amp; Alerts</h1>
              {unreadCount > 0 && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500 text-white">
                  {unreadCount} unread
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Field inspection triggers, critical defect flags, report publication, and maintenance reminders.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {(role === 'admin' || role === 'civil_engineer' || role === 'manager') && (
              <button
                onClick={handleTriggerSweep}
                disabled={isSweeping}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 shadow-sm transition disabled:opacity-50"
                title="Run background check for approaching deadlines and overdue inspections"
              >
                {isSweeping ? 'Sweeping...' : 'Check Deadlines'}
              </button>
            )}
            <button
              onClick={handleMarkAllRead}
              disabled={unreadCount === 0}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 shadow-sm transition disabled:opacity-50"
            >
              Mark All Read
            </button>
            <button
              onClick={openPreferencesModal}
              className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow transition flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Preferences
            </button>
          </div>
        </div>

        {/* Notifications / Alerts */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 font-bold">&times;</button>
          </div>
        )}
        {successMsg && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm flex justify-between items-center">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} className="text-green-500 hover:text-green-700 font-bold">&times;</button>
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-200 text-xs">
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setUnreadOnly(false); setPage(1); }}
              className={`font-semibold pb-2 border-b-2 transition ${!unreadOnly ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
            >
              All Notifications
            </button>
            <button
              onClick={() => { setUnreadOnly(true); setPage(1); }}
              className={`font-semibold pb-2 border-b-2 transition ${unreadOnly ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
            >
              Unread Only ({unreadCount})
            </button>
          </div>

          <span className="text-slate-400">Total {total} notifications</span>
        </div>

        {/* Notifications List */}
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-12 text-slate-400 text-xs">Loading notifications...</div>
          ) : notifications.length === 0 ? (
            <div className="bg-white p-12 rounded-xl border border-slate-200 text-center">
              <svg className="w-10 h-10 text-slate-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <p className="text-sm font-semibold text-slate-700">No notifications found.</p>
              <p className="text-xs text-slate-400 mt-1">You are all caught up!</p>
            </div>
          ) : (
            notifications.map((notif) => {
              const link = getEntityLink(notif)
              return (
                <div
                  key={notif.id}
                  className={`p-4 rounded-xl border transition flex items-start gap-3.5 ${
                    notif.is_read
                      ? 'bg-white border-slate-200 text-slate-600'
                      : 'bg-indigo-50/40 border-indigo-200 shadow-sm text-slate-900'
                  }`}
                >
                  <div className="pt-0.5 flex-shrink-0">
                    {!notif.is_read && (
                      <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 block mt-1.5" title="Unread" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      {getTypeBadge(notif.type)}
                      <h3 className="text-xs font-bold text-slate-900 truncate">{notif.title}</h3>
                      <span className="text-[11px] text-slate-400 ml-auto">
                        {new Date(notif.created_at).toLocaleString()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed mb-2">{notif.body}</p>

                    <div className="flex items-center gap-3 pt-1 text-[11px]">
                      {link && (
                        <Link
                          to={link}
                          className="font-semibold text-indigo-600 hover:text-indigo-800 transition flex items-center gap-1"
                        >
                          View {notif.entity_type} &rarr;
                        </Link>
                      )}
                      {!notif.is_read && (
                        <button
                          onClick={() => handleMarkRead(notif.id)}
                          className="text-slate-500 hover:text-slate-800 transition"
                        >
                          Mark as Read
                        </button>
                      )}
                      {notif.email_sent && (
                        <span className="text-slate-400 flex items-center gap-1" title="Email dispatched">
                          &bull; Email Sent
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Pagination */}
        {total > pageSize && (
          <div className="mt-6 flex items-center justify-between text-xs text-slate-500">
            <span>Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total}</span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                className="px-3 py-1 border rounded bg-white disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={page * pageSize >= total}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1 border rounded bg-white disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Preferences Modal */}
      {isPrefOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Notification Preferences</h3>
            <p className="text-xs text-slate-500 mb-4">
              Configure your delivery channels and minimum defect severity thresholds.
            </p>

            {prefLoading || !pref ? (
              <p className="text-center py-6 text-xs text-slate-400">Loading preferences...</p>
            ) : (
              <form onSubmit={handleSavePreferences} className="space-y-4 text-xs">
                <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={pref.in_app_enabled}
                      onChange={(e) => setPref({ ...pref, in_app_enabled: e.target.checked })}
                      className="rounded text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="font-semibold text-slate-700">In-App Notifications</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={pref.email_enabled}
                      onChange={(e) => setPref({ ...pref, email_enabled: e.target.checked })}
                      className="rounded text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="font-semibold text-slate-700">Email Notifications (SMTP)</span>
                  </label>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Minimum Defect Severity Threshold
                  </label>
                  <select
                    value={pref.min_severity}
                    onChange={(e) => setPref({ ...pref, min_severity: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="none">None (All defect notices)</option>
                    <option value="low">Low (Hairline cracks, minor spalling)</option>
                    <option value="medium">Medium (Moderate width cracks)</option>
                    <option value="high">High (Severe cracks, structural displacement)</option>
                    <option value="critical">Critical Only (Immediate review required)</option>
                  </select>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Alerts below this severity level will be suppressed from your notification stream.
                  </p>
                </div>

                <div className="flex justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setIsPrefOpen(false)}
                    className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSavingPref}
                    className="px-4 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {isSavingPref ? 'Saving...' : 'Save Preferences'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
export default Notifications
