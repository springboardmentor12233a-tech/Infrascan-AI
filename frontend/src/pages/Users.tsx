import React, { useEffect, useState } from 'react'
import { Navbar } from '../components/Navbar'
import { usersApi, type User } from '../api/client'
import { useAuth } from '../context/AuthContext'

const ROLES = [
  'inspector',
  'civil_engineer',
  'maintenance_engineer',
  'manager',
  'admin',
]

export const Users: React.FC = () => {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  // Filters & Pagination
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [total, setTotal] = useState(0)

  // Create User Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createRole, setCreateRole] = useState('inspector')
  const [createPassword, setCreatePassword] = useState('')
  const [createLoading, setCreateLoading] = useState(false)

  // Force reset modal
  const [resetTokenData, setResetTokenData] = useState<{ email: string; token: string } | null>(null)

  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await usersApi.listUsers({
        search: search.trim() || undefined,
        role: roleFilter || undefined,
        is_active: activeFilter === 'true' ? true : activeFilter === 'false' ? false : undefined,
        page,
        page_size: pageSize,
      })
      setUsers(data.items)
      setTotal(data.total)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load users list.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [page, roleFilter, activeFilter])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadUsers()
  }

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await usersApi.updateRole(userId, newRole)
      setActionMessage(`Role updated to ${newRole} for user #${userId}`)
      await loadUsers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user role.')
    }
  }

  const handleToggleActive = async (userId: number, currentStatus: boolean) => {
    if (userId === currentUser?.user_id && currentStatus) {
      setError('You cannot deactivate your own account.')
      return
    }
    try {
      await usersApi.updateActiveStatus(userId, !currentStatus)
      setActionMessage(`User #${userId} ${!currentStatus ? 'activated' : 'deactivated'}`)
      await loadUsers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user status.')
    }
  }

  const handleForceReset = async (user: User) => {
    if (!confirm(`Generate a one-time password reset token for ${user.email} and revoke all current sessions?`)) {
      return
    }
    try {
      const res = await usersApi.forceResetPassword(user.user_id)
      setResetTokenData({ email: user.email, token: res.reset_token })
      setActionMessage(`Reset token generated for ${user.email}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to trigger password reset.')
    }
  }

  const handleRevokeSessions = async (user: User) => {
    if (!confirm(`Revoke all active sessions for ${user.email}? The user will be signed out immediately.`)) {
      return
    }
    try {
      const res = await usersApi.revokeUserSessions(user.user_id)
      setActionMessage(res.message)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to revoke user sessions.')
    }
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (createPassword.length < 10) {
      setError('Password must be at least 10 characters long.')
      return
    }
    setCreateLoading(true)
    setError(null)
    try {
      await usersApi.createUser({
        full_name: createName.trim(),
        email: createEmail.trim(),
        role: createRole,
        password: createPassword,
      })
      setActionMessage(`User ${createEmail} created with role ${createRole}.`)
      setIsCreateOpen(false)
      setCreateName('')
      setCreateEmail('')
      setCreatePassword('')
      setPage(1)
      await loadUsers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create user.')
    } finally {
      setCreateLoading(false)
    }
  }

  const totalPages = Math.ceil(total / pageSize) || 1

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">User Administration</h1>
            <p className="text-xs text-slate-500 mt-1">
              Manage accounts, role-based access control, active sessions, and password resets.
            </p>
          </div>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            Create User
          </button>
        </div>

        {actionMessage && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex justify-between items-center">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="text-emerald-600 font-bold">&times;</button>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-600 font-bold">&times;</button>
          </div>
        )}

        {/* Filter bar */}
        <form onSubmit={handleSearch} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-semibold text-slate-700 mb-1">Search Name / Email</label>
            <input
              type="text"
              placeholder="Search by user name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Role</label>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value)
                setPage(1)
              }}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Roles</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Status</label>
            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value)
                setPage(1)
              }}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Statuses</option>
              <option value="true">Active Only</option>
              <option value="false">Inactive Only</option>
            </select>
          </div>
          <button
            type="submit"
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            Apply
          </button>
        </form>

        {/* Users Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">User</th>
                  <th className="px-4 py-3 text-left">Role</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      Loading users...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      No users match the criteria.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.user_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-500">#{u.user_id}</td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-800">{u.full_name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{u.email}</div>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.user_id, e.target.value)}
                          className="px-2 py-1 border border-slate-300 rounded text-xs font-medium text-slate-800 bg-white"
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                          u.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                        <button
                          onClick={() => handleToggleActive(u.user_id, u.is_active)}
                          className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                            u.is_active
                              ? 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200'
                              : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
                          }`}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button
                          onClick={() => handleForceReset(u)}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition"
                          title="Generate reset token"
                        >
                          Reset Pass
                        </button>
                        <button
                          onClick={() => handleRevokeSessions(u)}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition"
                          title="Revoke all active sessions"
                        >
                          Revoke Sessions
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Showing page {page} of {totalPages} ({total} total users)
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 bg-white border border-slate-300 rounded text-xs font-medium text-slate-700 disabled:opacity-40 hover:bg-slate-50"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-white border border-slate-300 rounded text-xs font-medium text-slate-700 disabled:opacity-40 hover:bg-slate-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {/* Create User Modal */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-base font-bold text-slate-900">Create New User</h2>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-slate-400 hover:text-slate-600 text-lg font-bold"
                >
                  &times;
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    placeholder="e.g. Marcus Miller"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={createEmail}
                    onChange={(e) => setCreateEmail(e.target.value)}
                    placeholder="marcus@agency.gov"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Assigned Role</label>
                  <select
                    value={createRole}
                    onChange={(e) => setCreateRole(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Initial Password (min 10 characters)
                  </label>
                  <input
                    type="password"
                    required
                    minLength={10}
                    value={createPassword}
                    onChange={(e) => setCreatePassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg font-medium text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createLoading}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg font-semibold shadow-sm"
                  >
                    {createLoading ? 'Creating...' : 'Create Account'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Force Reset Token Display Modal */}
        {resetTokenData && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200">
              <h2 className="text-base font-bold text-slate-900 mb-2">Password Reset Token Generated</h2>
              <p className="text-xs text-slate-600 mb-4">
                Share this single-use reset token securely with <strong className="text-slate-800">{resetTokenData.email}</strong>.
                It is valid for 1 hour and can be used on the Reset Password page.
              </p>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg font-mono text-xs text-slate-800 break-all select-all mb-4">
                {resetTokenData.token}
              </div>
              <div className="flex justify-end">
                <button
                  onClick={() => setResetTokenData(null)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default Users
