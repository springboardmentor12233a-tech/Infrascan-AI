import React, { useEffect, useState } from 'react'
import { Navbar } from '../components/Navbar'
import { usersApi, type User } from '../api/client'

const ROLES = [
  'inspector',
  'civil_engineer',
  'maintenance_engineer',
  'manager',
  'admin',
]

export const Users: React.FC = () => {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  // Fetch all registered users
  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await usersApi.getUsers()
      setUsers(data)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load users list.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  // Handle role change
  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await usersApi.updateRole(userId, newRole)
      setActionMessage(`Role updated to ${newRole} for user #${userId}`)
      await loadUsers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user role.')
    }
  }

  // Handle active status toggle
  const handleToggleActive = async (userId: number, currentStatus: boolean) => {
    try {
      await usersApi.updateActiveStatus(userId, !currentStatus)
      setActionMessage(
        `User #${userId} ${!currentStatus ? 'activated' : 'deactivated'}`,
      )
      await loadUsers()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user status.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
              User Management
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Admin controls: view users, adjust role permissions, and toggle account activation.
            </p>
          </div>
          <button
            onClick={loadUsers}
            className="px-3.5 py-1.5 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm"
          >
            Refresh
          </button>
        </div>

        {/* Action alerts */}
        {actionMessage && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">
            {actionMessage}
          </div>
        )}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm">
            {error}
          </div>
        )}

        {/* Users Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-500 animate-pulse">
              Loading users registry...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 font-semibold">
                  <tr>
                    <th className="px-6 py-3.5">ID</th>
                    <th className="px-6 py-3.5">Name</th>
                    <th className="px-6 py-3.5">Email</th>
                    <th className="px-6 py-3.5">Role</th>
                    <th className="px-6 py-3.5">Status</th>
                    <th className="px-6 py-3.5">Created</th>
                    <th className="px-6 py-3.5 text-right">Toggle Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {users.map((u) => (
                    <tr key={u.user_id} className="hover:bg-slate-50/80">
                      <td className="px-6 py-4 font-mono text-xs text-slate-500">
                        #{u.user_id}
                      </td>
                      <td className="px-6 py-4 font-medium text-slate-900">
                        {u.full_name}
                      </td>
                      <td className="px-6 py-4 text-slate-600">{u.email}</td>
                      <td className="px-6 py-4">
                        <select
                          value={u.role}
                          onChange={(e) =>
                            handleRoleChange(u.user_id, e.target.value)
                          }
                          className="bg-slate-50 border border-slate-300 rounded px-2.5 py-1 text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r.replace('_', ' ')}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                            u.is_active
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-rose-50 text-rose-700'
                          }`}
                        >
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() =>
                            handleToggleActive(u.user_id, u.is_active)
                          }
                          className={`px-3 py-1 rounded text-xs font-medium border transition-colors ${
                            u.is_active
                              ? 'border-rose-200 text-rose-700 hover:bg-rose-50'
                              : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'
                          }`}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
