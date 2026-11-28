import { useState } from 'react'
import { Plus, Calendar, CheckCircle2 } from 'lucide-react'
import { MOCK_MAINTENANCE_TASKS, MOCK_ASSETS, MOCK_USERS } from '@/data/mockData'
import { MAINTENANCE_PRIORITIES } from '@/lib/constants'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Modal } from '@/components/ui/Modal'
import type { MaintenanceTask, MaintenancePriority, MaintenanceStatus } from '@/types'

export function MaintenancePage() {
  const [tasks, setTasks] = useState<MaintenanceTask[]>(MOCK_MAINTENANCE_TASKS)
  const [priorityFilter, setPriorityFilter] = useState('All')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    title: '',
    assetId: MOCK_ASSETS[0].id,
    priority: 'High Priority' as MaintenancePriority,
    assignedTo: MOCK_USERS[0].name,
    dueDate: '2026-12-10',
    description: '',
  })

  const filtered = tasks.filter((t) => priorityFilter === 'All' || t.priority === priorityFilter)

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    const asset = MOCK_ASSETS.find((a) => a.id === form.assetId) || MOCK_ASSETS[0]
    const created: MaintenanceTask = {
      id: `MNT-${305 + tasks.length}`,
      title: form.title,
      assetId: asset.id,
      assetName: asset.name,
      priority: form.priority,
      status: 'Open',
      assignedTo: form.assignedTo,
      dueDate: form.dueDate,
      createdAt: new Date().toISOString().slice(0, 10),
      estimatedCostUsd: 5000,
      description: form.description,
      followUpInspectionRequired: true,
    }
    setTasks([created, ...tasks])
    setShowCreate(false)
    setForm({ ...form, title: '', description: '' })
  }

  const updateStatus = (id: string, status: MaintenanceStatus) => {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, status } : t)))
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Maintenance Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">Track structural repairs, priorities, and follow-up inspections</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
        >
          <Plus className="w-4 h-4" /> New Maintenance Task
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {['All', ...MAINTENANCE_PRIORITIES].map((p) => (
          <button
            key={p}
            onClick={() => setPriorityFilter(p)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium border ${
              priorityFilter === p
                ? 'bg-[#0F2942] text-white border-[#0F2942]'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">Task ID</th>
                <th className="px-4 py-3 font-medium">Title & Asset</th>
                <th className="px-4 py-3 font-medium">Priority</th>
                <th className="px-4 py-3 font-medium">Assigned To</th>
                <th className="px-4 py-3 font-medium">Due Date</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Update</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((task) => (
                <tr key={task.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-medium text-slate-800">{task.id}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{task.title}</p>
                    <p className="text-[11px] text-slate-500">{task.assetName}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-700 font-medium">{task.priority}</td>
                  <td className="px-4 py-3 text-slate-600">{task.assignedTo}</td>
                  <td className="px-4 py-3 text-slate-600">
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" /> {task.dueDate}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    {task.status !== 'Completed' && (
                      <button
                        onClick={() => updateStatus(task.id, 'Completed')}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Complete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Maintenance Task">
        <form onSubmit={handleCreate} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">Task Title</label>
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-md"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Asset</label>
              <select
                value={form.assetId}
                onChange={(e) => setForm({ ...form, assetId: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white"
              >
                {MOCK_ASSETS.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value as MaintenancePriority })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white"
              >
                {MAINTENANCE_PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Assigned Engineer</label>
              <select
                value={form.assignedTo}
                onChange={(e) => setForm({ ...form, assignedTo: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white"
              >
                {MOCK_USERS.map((u) => (
                  <option key={u.id} value={u.name}>
                    {u.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Due Date</label>
              <input
                type="date"
                value={form.dueDate}
                onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border border-slate-200 rounded-md">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 bg-[#0F2942] text-white rounded-md font-medium">
              Create Task
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

