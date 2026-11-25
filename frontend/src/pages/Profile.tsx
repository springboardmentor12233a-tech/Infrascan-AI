import React, { useEffect, useState } from 'react'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import { authApi, usersApi, type UserSession } from '../api/client'

export const Profile: React.FC = () => {
  const { user, refreshUser } = useAuth()

  // State for updating full name
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [nameLoading, setNameLoading] = useState(false)
  const [nameMessage, setNameMessage] = useState<{
    text: string
    isError: boolean
  } | null>(null)

  // State for changing password
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState<{
    text: string
    isError: boolean
  } | null>(null)

  // Sessions state
  const [sessions, setSessions] = useState<UserSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState<boolean>(true)
  const [sessionMessage, setSessionMessage] = useState<string | null>(null)

  const loadSessions = async () => {
    setSessionsLoading(true)
    try {
      const data = await authApi.getSessions()
      setSessions(data)
    } catch {
      // ignore
    } finally {
      setSessionsLoading(false)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  // Handle name update
  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault()
    setNameMessage(null)
    setNameLoading(true)

    try {
      await usersApi.updateMe(fullName)
      await refreshUser()
      setNameMessage({ text: 'Full name updated successfully!', isError: false })
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to update full name. Please try again.'
      setNameMessage({ text: msg, isError: true })
    } finally {
      setNameLoading(false)
    }
  }

  // Handle password change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordMessage(null)

    if (newPassword.length < 10) {
      setPasswordMessage({
        text: 'New password must be at least 10 characters.',
        isError: true,
      })
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordMessage({
        text: 'Passwords do not match.',
        isError: true,
      })
      return
    }

    setPasswordLoading(true)
    try {
      const res = await usersApi.changePassword(oldPassword, newPassword)
      setPasswordMessage({ text: res.message, isError: false })
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await loadSessions()
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to change password. Please verify current password.'
      setPasswordMessage({ text: msg, isError: true })
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await authApi.revokeSession(sessionId)
      setSessionMessage('Session successfully revoked.')
      await loadSessions()
    } catch (err: any) {
      setSessionMessage(err.response?.data?.detail || 'Failed to revoke session.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Account & Security</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage your personal credentials, session tokens, and security settings.
          </p>
        </div>

        {/* Read-Only Account Details */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
            Profile Information
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-400 block font-medium">Email Address</span>
              <span className="text-slate-800 font-mono font-semibold">{user?.email}</span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Assigned Role</span>
              <span className="inline-flex items-center px-2 py-0.5 mt-0.5 rounded text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                {user?.role}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Account Status</span>
              <span className="text-emerald-700 font-semibold">Active</span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Member Since</span>
              <span className="text-slate-700">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Edit Name Form */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
            Edit Full Name
          </h2>

          {nameMessage && (
            <div
              className={`mb-4 p-3 rounded-lg text-xs font-medium ${
                nameMessage.isError
                  ? 'bg-rose-50 border border-rose-200 text-rose-800'
                  : 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              }`}
            >
              {nameMessage.text}
            </div>
          )}

          <form onSubmit={handleUpdateName} className="space-y-4 max-w-md">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <button
              type="submit"
              disabled={nameLoading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition"
            >
              {nameLoading ? 'Saving...' : 'Update Name'}
            </button>
          </form>
        </div>

        {/* Change Password Form */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            Change Password
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Updating your password will immediately sign out all other devices and active sessions.
          </p>

          {passwordMessage && (
            <div
              className={`mb-4 p-3 rounded-lg text-xs font-medium ${
                passwordMessage.isError
                  ? 'bg-rose-50 border border-rose-200 text-rose-800'
                  : 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              }`}
            >
              {passwordMessage.text}
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Current Password
              </label>
              <input
                type="password"
                required
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                New Password (minimum 10 characters)
              </label>
              <input
                type="password"
                required
                minLength={10}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                required
                minLength={10}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <button
              type="submit"
              disabled={passwordLoading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition"
            >
              {passwordLoading ? 'Updating Password...' : 'Change Password & Revoke Sessions'}
            </button>
          </form>
        </div>

        {/* Active Sessions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Active Sessions &amp; Devices
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Manage your authenticated sessions across different browsers and devices.
              </p>
            </div>
            <button
              onClick={loadSessions}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Refresh
            </button>
          </div>

          {sessionMessage && (
            <div className="mb-4 p-3 bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs">
              {sessionMessage}
            </div>
          )}

          {sessionsLoading ? (
            <div className="text-center py-6 text-xs text-slate-400">Loading active sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-400">No active refresh sessions found.</div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {sessions.map((sess) => (
                <div key={sess.session_id} className="py-3 flex items-center justify-between gap-4">
                  <div>
                    <div className="font-semibold text-slate-800">
                      {sess.ip ? `IP Address: ${sess.ip}` : 'Unknown IP'}
                    </div>
                    <div className="text-[11px] text-slate-500 max-w-md truncate" title={sess.user_agent || ''}>
                      {sess.user_agent || 'Client Application'}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Last used: {new Date(sess.last_used_at).toLocaleString()}
                    </div>
                  </div>
                  <button
                    onClick={() => handleRevokeSession(sess.session_id)}
                    className="px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded text-xs font-medium transition"
                  >
                    Revoke
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default Profile
