import React, { useState } from 'react'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import { usersApi } from '../api/client'

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
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState<{
    text: string
    isError: boolean
  } | null>(null)

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
      const msg =
        err.response?.data?.detail || 'Failed to update full name. Please try again.'
      setNameMessage({ text: msg, isError: true })
    } finally {
      setNameLoading(false)
    }
  }

  // Handle password change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordMessage(null)

    if (newPassword.length < 8) {
      setPasswordMessage({
        text: 'New password must be at least 8 characters.',
        isError: true,
      })
      return
    }

    setPasswordLoading(true)
    try {
      const res = await usersApi.changePassword(oldPassword, newPassword)
      setPasswordMessage({
        text: res.message || 'Password changed successfully!',
        isError: false,
      })
      setOldPassword('')
      setNewPassword('')
    } catch (err: any) {
      const msg =
        err.response?.data?.detail || 'Failed to change password. Check your current password.'
      setPasswordMessage({ text: msg, isError: true })
    } finally {
      setPasswordLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight mb-6">
          Your Profile
        </h1>

        <div className="space-y-6">
          {/* Account Overview Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Account Overview
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-400 block text-xs">Email</span>
                <span className="font-medium text-slate-700">{user?.email}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Role</span>
                <span className="inline-block px-2.5 py-0.5 text-xs font-semibold rounded bg-indigo-50 text-indigo-700 uppercase">
                  {user?.role.replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Status</span>
                <span className="text-emerald-600 font-medium">Active</span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Member Since</span>
                <span className="text-slate-700">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Edit Profile Form */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Edit Name
            </h2>

            {nameMessage && (
              <div
                className={`mb-4 p-3 rounded-lg text-sm ${
                  nameMessage.isError
                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}
              >
                {nameMessage.text}
              </div>
            )}

            <form onSubmit={handleUpdateName} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full max-w-md px-3.5 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={nameLoading}
                className="py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm shadow transition-colors disabled:opacity-50"
              >
                {nameLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Change Password
            </h2>

            {passwordMessage && (
              <div
                className={`mb-4 p-3 rounded-lg text-sm ${
                  passwordMessage.isError
                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}
              >
                {passwordMessage.text}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  required
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  New Password (min 8 characters)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={passwordLoading}
                className="py-2 px-4 bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-lg text-sm shadow transition-colors disabled:opacity-50"
              >
                {passwordLoading ? 'Updating Password...' : 'Update Password'}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}
