import { useState } from 'react'
import { Plus } from 'lucide-react'
import { MOCK_USERS } from '@/data/mockData'
import { USER_ROLES } from '@/lib/constants'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Modal } from '@/components/ui/Modal'
import type { UserAccount, UserRole } from '@/types'

export function UserManagementPage() {
  const [users, setUsers] = useState<UserAccount[]>(MOCK_USERS)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({
    name: '',
    email: '',
    role: 'Civil Engineer' as UserRole,
    department: 'Structural Bridges Division',
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    const created: UserAccount = {
      id: `USR-0${users.length + 1}`,
      name: form.name,
      email: form.email,
      role: form.role,
      department: form.department,
      status: 'Active',
      lastActive: new Date().toISOString(),
      avatarInitials: form.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2),
    }
    setUsers([created, ...users])
    setShowAdd(false)
    setForm({ ...form, name: '', email: '' })
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">User Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manage engineering roles, departments, and platform permissions</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
        >
          <Plus className="w-4 h-4" /> Add User
        </button>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Department</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-[#0F2942] text-white flex items-center justify-center text-[11px] font-semibold">
                      {u.avatarInitials}
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{u.name}</p>
                      <p className="text-[11px] text-slate-500">{u.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-700">{u.role}</td>
                <td className="px-4 py-3 text-slate-600">{u.department}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={u.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Platform User">
        <form onSubmit={handleAdd} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">Full Name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-md"
            />
          </div>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Email</label>
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-md"
            />
          </div>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
              className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white"
            >
              {USER_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setShowAdd(false)} className="px-4 py-2 border border-slate-200 rounded-md">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 bg-[#0F2942] text-white rounded-md font-medium">
              Add User
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

