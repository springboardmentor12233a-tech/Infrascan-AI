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
      setActionMessage(`Role updated to ${newRole.replace('_', ' ')} for user #${userId}`)
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
    <div className="min-h-screen bg-[#141619] text-white flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-[#2C2E3A] gap-4">
          <div>
            <div className="text-xs font-mono font-semibold text-[#0A21C0] uppercase tracking-wider mb-1">
              Identity & Access Management
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              User & Role Management
            </h1>
            <p className="text-xs sm:text-sm text-[#B3B4BD] mt-1">
              Admin governance: role-based access control (RBAC), engineering clearances, and inspector activation.
            </p>
          </div>
          <button
            onClick={loadUsers}
            className="px-4 py-2 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-white rounded-full text-xs font-semibold transition-all cursor-pointer shrink-0"
          >
            🔄 Refresh Registry
          </button>
        </div>

        {/* Action alerts */}
        {actionMessage && (
          <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs sm:text-sm rounded-xl">
            {actionMessage}
          </div>
        )}
        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs sm:text-sm rounded-xl">
            {error}
          </div>
        )}

        {/* Users Table */}
        <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] overflow-hidden shadow-xl">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#B3B4BD] animate-pulse">
              <div className="w-8 h-8 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              Loading team directory and access permissions...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-[#141619] text-left text-xs">
                <thead className="bg-[#141619]/80 text-[#B3B4BD] font-mono text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4">ID</th>
                    <th className="px-6 py-4">Full Name</th>
                    <th className="px-6 py-4">Corporate Email</th>
                    <th className="px-6 py-4">Assigned Role</th>
                    <th className="px-6 py-4">Account Status</th>
                    <th className="px-6 py-4">Registered Date</th>
                    <th className="px-6 py-4 text-right">Access Controls</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#141619]/60 text-white">
                  {users.map((u) => (
                    <tr key={u.user_id} className="hover:bg-[#141619]/40 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-[#0A21C0]">
                        #{u.user_id}
                      </td>
                      <td className="px-6 py-4 font-semibold text-white">
                        {u.full_name}
                      </td>
                      <td className="px-6 py-4 text-[#B3B4BD] font-mono">
                        {u.email}
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={u.role}
                          onChange={(e) =>
                            handleRoleChange(u.user_id, e.target.value)
                          }
                          className="bg-[#141619] border border-[#2C2E3A] rounded-xl px-2.5 py-1 text-xs font-semibold text-white focus:outline-none focus:border-[#0A21C0]"
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r.replace('_', ' ').toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            u.is_active
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {u.is_active ? 'Active' : 'Suspended'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-[#B3B4BD]">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() =>
                            handleToggleActive(u.user_id, u.is_active)
                          }
                          className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                            u.is_active
                              ? 'bg-rose-950/40 hover:bg-rose-900 border border-rose-500/30 text-rose-300'
                              : 'bg-emerald-950/40 hover:bg-emerald-900 border border-emerald-500/30 text-emerald-300'
                          }`}
                        >
                          {u.is_active ? 'Suspend' : 'Reactivate'}
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

export default Users
