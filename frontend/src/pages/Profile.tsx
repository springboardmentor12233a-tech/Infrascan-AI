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
    <div className="min-h-screen bg-[#141619] text-white flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <div className="text-xs font-mono font-semibold text-[#0A21C0] uppercase tracking-wider mb-1">
            Personnel Account
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            User Profile & Security
          </h1>
          <p className="text-xs sm:text-sm text-[#B3B4BD] mt-1">
            Manage your personal profile details, inspect credentials, and update password.
          </p>
        </div>

        <div className="space-y-6">
          {/* Account Overview Card */}
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-[#0A21C0]/10 rounded-full blur-3xl pointer-events-none"></div>

            <h2 className="text-xs font-bold uppercase tracking-wider text-[#0A21C0] mb-4">
              Account Overview
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Registered Email</span>
                <span className="font-semibold text-white font-mono">{user?.email}</span>
              </div>
              <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Engineering Role</span>
                <span className="inline-block px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-[#050A44] text-blue-300 border border-[#0A21C0]/30 uppercase">
                  {user?.role.replace('_', ' ')}
                </span>
              </div>
              <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Account State</span>
                <span className="text-emerald-400 font-semibold flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
                  <span>Active & Verified</span>
                </span>
              </div>
              <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Member Since</span>
                <span className="text-white font-semibold">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Edit Profile Form */}
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#0A21C0] mb-4">
              Edit Display Name
            </h2>

            {nameMessage && (
              <div
                className={`mb-4 p-3 rounded-xl text-xs ${
                  nameMessage.isError
                    ? 'bg-rose-950/40 text-rose-300 border border-rose-500/40'
                    : 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/40'
                }`}
              >
                {nameMessage.text}
              </div>
            )}

            <form onSubmit={handleUpdateName} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#B3B4BD] mb-1">
                  Full Legal Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full max-w-md px-4 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={nameLoading}
                className="py-2.5 px-6 bg-[#0A21C0] hover:bg-[#081ba0] text-white font-semibold rounded-full text-xs shadow-md shadow-[#0A21C0]/30 transition-all disabled:opacity-50 cursor-pointer"
              >
                {nameLoading ? 'Saving...' : 'Save Name'}
              </button>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#0A21C0] mb-4">
              Change Security Password
            </h2>

            {passwordMessage && (
              <div
                className={`mb-4 p-3 rounded-xl text-xs ${
                  passwordMessage.isError
                    ? 'bg-rose-950/40 text-rose-300 border border-rose-500/40'
                    : 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/40'
                }`}
              >
                {passwordMessage.text}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div>
                <label className="block text-xs font-medium text-[#B3B4BD] mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  required
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#B3B4BD] mb-1">
                  New Password (min 8 characters)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={passwordLoading}
                className="py-2.5 px-6 bg-[#0A21C0] hover:bg-[#081ba0] text-white font-semibold rounded-full text-xs shadow-md shadow-[#0A21C0]/30 transition-all disabled:opacity-50 cursor-pointer"
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

export default Profile
