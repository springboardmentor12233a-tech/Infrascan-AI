import React, { useEffect, useState, useCallback } from 'react'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import {
  maintenanceApi,
  assetsApi,
  usersApi,
  type InfrastructureAsset,
  type User as UserType,
} from '../api/client'

export interface MaintenanceTaskItem {
  task_id: number
  asset_id: number
  asset_name?: string
  inspection_id?: number
  priority_id?: number
  title: string
  description?: string
  task_type?: string
  priority: string // P1, P2, P3, P4
  status: string // open, assigned, in_progress, completed, verified
  assigned_to?: number
  assignee_name?: string
  created_by?: number
  due_date?: string
  started_at?: string
  completed_at?: string
  resolution_notes?: string
  created_at?: string
}

export const Maintenance: React.FC = () => {
  const { user } = useAuth()
  const isMaintenanceEng = user?.role === 'maintenance_engineer'
  const isEngineerOrManager = ['admin', 'manager', 'civil_engineer'].includes(user?.role || '')

  // State
  const [tasks, setTasks] = useState<MaintenanceTaskItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')

  // Modals & Forms
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isCompleteOpen, setIsCompleteOpen] = useState(false)
  const [isVerifyOpen, setIsVerifyOpen] = useState(false)
  const [activeTask, setActiveTask] = useState<MaintenanceTaskItem | null>(null)

  // Creation form state
  const [assets, setAssets] = useState<InfrastructureAsset[]>([])
  const [engineers, setEngineers] = useState<UserType[]>([])
  const [newAssetId, setNewAssetId] = useState<number>(0)
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newPriority, setNewPriority] = useState('P2')
  const [newAssignedTo, setNewAssignedTo] = useState<number | undefined>(undefined)
  const [newDueDate, setNewDueDate] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Completion form state
  const [completionNotes, setCompletionNotes] = useState('')

  // Verification form state
  const [verifyComment, setVerifyComment] = useState('')
  const [verifyApproved, setVerifyApproved] = useState(true)

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (statusFilter !== 'all') params.status = statusFilter
      const data = await maintenanceApi.listTasks(params)
      setTasks(data)
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load maintenance tasks.')
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  // Real-time listener for task and priority updates
  useEffect(() => {
    const handleLiveEvent = (e: Event) => {
      const customEvent = e as CustomEvent
      const type = customEvent.detail?.type || ''
      if (type.startsWith('task.') || type.startsWith('priority.')) {
        loadTasks()
      }
    }
    window.addEventListener('infrascan:event', handleLiveEvent)
    return () => window.removeEventListener('infrascan:event', handleLiveEvent)
  }, [loadTasks])

  // Load auxiliary data for task creation
  useEffect(() => {
    if (isEngineerOrManager) {
      assetsApi.list({ page_size: 100 }).then((res) => {
        setAssets(res.items)
        if (res.items.length > 0 && newAssetId === 0) {
          setNewAssetId(res.items[0].asset_id)
        }
      }).catch(() => {})

      usersApi.listUsers({ page_size: 100, role: 'maintenance_engineer' }).then((res) => {
        setEngineers(res.items)
      }).catch(() => {})
    }
  }, [isEngineerOrManager, newAssetId])

  const handleStartTask = async (taskId: number) => {
    try {
      await maintenanceApi.updateStatus(taskId, 'in_progress')
      await loadTasks()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update task status.')
    }
  }

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeTask) return
    try {
      setSubmitting(true)
      await maintenanceApi.updateStatus(activeTask.task_id, 'completed', completionNotes)
      setIsCompleteOpen(false)
      setActiveTask(null)
      setCompletionNotes('')
      await loadTasks()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to complete task.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeTask) return
    try {
      setSubmitting(true)
      await maintenanceApi.verifyTask(activeTask.task_id, verifyApproved, verifyComment)
      setIsVerifyOpen(false)
      setActiveTask(null)
      setVerifyComment('')
      await loadTasks()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to verify task.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSubmitting(true)
      await maintenanceApi.createTask({
        asset_id: newAssetId,
        title: newTitle,
        description: newDescription,
        priority: newPriority,
        assigned_to: newAssignedTo,
        due_date: newDueDate ? new Date(newDueDate).toISOString() : undefined,
      })
      setIsCreateOpen(false)
      setNewTitle('')
      setNewDescription('')
      setNewPriority('P2')
      setNewDueDate('')
      await loadTasks()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create task.')
    } finally {
      setSubmitting(false)
    }
  }

  const filteredTasks = tasks.filter((t) => {
    if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false
    return true
  })

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'P1':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">P1 - Critical</span>
      case 'P2':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">P2 - High</span>
      case 'P3':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 text-yellow-800 border border-yellow-300">P3 - Medium</span>
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-300">P4 - Low</span>
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">Open</span>
      case 'assigned':
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Assigned</span>
      case 'in_progress':
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 animate-pulse">In Progress</span>
      case 'completed':
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">Completed (Needs Verification)</span>
      case 'verified':
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">Verified</span>
      default:
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">{status}</span>
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Banner */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight flex items-center space-x-3">
              <span>Maintenance Work Orders</span>
              <span className="text-xs px-2.5 py-1 rounded bg-indigo-50 text-indigo-700 font-semibold uppercase">
                {user?.role.replace('_', ' ')}
              </span>
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Dispatch, track, and verify civil repair tasks based on AI defect detections and engineering reviews.
            </p>
            <p className="text-xs text-amber-700 mt-1 font-medium bg-amber-50 px-2 py-0.5 rounded inline-block">
              AI result for engineer review, not a final structural safety verdict.
            </p>
          </div>

          {isEngineerOrManager && (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="mt-4 md:mt-0 inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition"
            >
              + Create Maintenance Task
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6 flex flex-wrap gap-4 items-center justify-between">
          <div className="flex items-center space-x-3">
            <label className="text-xs font-medium text-slate-500">Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="assigned">Assigned</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="verified">Verified</option>
            </select>

            <label className="text-xs font-medium text-slate-500 ml-4">Priority:</label>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Priorities</option>
              <option value="P1">P1 - Critical</option>
              <option value="P2">P2 - High</option>
              <option value="P3">P3 - Medium</option>
              <option value="P4">P4 - Low</option>
            </select>
          </div>

          <span className="text-xs text-slate-400">
            Showing {filteredTasks.length} task{filteredTasks.length === 1 ? '' : 's'}
          </span>
        </div>

        {/* Task Cards List */}
        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-600 border-t-transparent mb-3" />
            <p className="text-sm">Loading maintenance tasks...</p>
          </div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-700 text-sm">
            {error}
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <p className="text-base font-semibold text-slate-700">No maintenance tasks found</p>
            <p className="text-xs text-slate-400 mt-1">
              {isMaintenanceEng
                ? 'No maintenance tasks are currently assigned to you.'
                : 'No tasks match the active filters.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredTasks.map((t) => (
              <div
                key={t.task_id}
                className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 hover:border-slate-300 transition"
              >
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1 mb-2">
                      {getPriorityBadge(t.priority)}
                      {getStatusBadge(t.status)}
                      <span className="text-xs text-slate-400 font-mono">Task #{t.task_id}</span>
                      {t.asset_name && (
                        <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                          {t.asset_name}
                        </span>
                      )}
                    </div>

                    <h2 className="text-base font-bold text-slate-800">{t.title}</h2>
                    {t.description && (
                      <p className="text-sm text-slate-600 mt-1 leading-relaxed">{t.description}</p>
                    )}

                    <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
                      <div>
                        Assigned To:{' '}
                        <span className="font-medium text-slate-600">
                          {t.assignee_name || (t.assigned_to ? `User #${t.assigned_to}` : 'Unassigned')}
                        </span>
                      </div>
                      {t.due_date && (
                        <div>
                          Due Date:{' '}
                          <span className="font-medium text-slate-600">
                            {new Date(t.due_date).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      {t.started_at && (
                        <div>
                          Started:{' '}
                          <span className="font-medium text-slate-600">
                            {new Date(t.started_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      {t.completed_at && (
                        <div>
                          Completed:{' '}
                          <span className="font-medium text-slate-600">
                            {new Date(t.completed_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>

                    {t.resolution_notes && (
                      <div className="mt-3 p-3 bg-slate-50 border border-slate-100 rounded-lg text-xs text-slate-700">
                        <span className="font-bold text-slate-500 block mb-0.5">Resolution Notes:</span>
                        {t.resolution_notes}
                      </div>
                    )}
                  </div>

                  {/* Actions column */}
                  <div className="flex md:flex-col gap-2 shrink-0">
                    {/* Maintenance Engineer Actions */}
                    {isMaintenanceEng && (
                      <>
                        {t.status === 'assigned' && (
                          <button
                            onClick={() => handleStartTask(t.task_id)}
                            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition"
                          >
                            Start Work
                          </button>
                        )}
                        {t.status === 'in_progress' && (
                          <button
                            onClick={() => {
                              setActiveTask(t)
                              setIsCompleteOpen(true)
                            }}
                            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition"
                          >
                            Complete Task
                          </button>
                        )}
                      </>
                    )}

                    {/* Civil Engineer / Admin Actions */}
                    {['admin', 'civil_engineer'].includes(user?.role || '') && t.status === 'completed' && (
                      <button
                        onClick={() => {
                          setActiveTask(t)
                          setIsVerifyOpen(true)
                        }}
                        className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition"
                      >
                        Verify Completion
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal: Create Maintenance Task */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 border border-slate-100">
              <h2 className="text-lg font-bold text-slate-800 mb-4">Create Maintenance Task</h2>
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Infrastructure Asset</label>
                  <select
                    value={newAssetId}
                    onChange={(e) => setNewAssetId(Number(e.target.value))}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    required
                  >
                    {assets.map((a) => (
                      <option key={a.asset_id} value={a.asset_id}>
                        {a.name} ({a.asset_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Task Title</label>
                  <input
                    type="text"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. Surface Crack Sealing on Pier 3"
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Description</label>
                  <textarea
                    value={newDescription}
                    onChange={(e) => setNewDescription(e.target.value)}
                    placeholder="Detailed repair instructions and safety notes..."
                    rows={3}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Priority</label>
                    <select
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value)}
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    >
                      <option value="P1">P1 - Critical (24-48 hrs)</option>
                      <option value="P2">P2 - High (1-2 weeks)</option>
                      <option value="P3">P3 - Medium (30 days)</option>
                      <option value="P4">P4 - Low (Routine)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Assignee</label>
                    <select
                      value={newAssignedTo || ''}
                      onChange={(e) => setNewAssignedTo(e.target.value ? Number(e.target.value) : undefined)}
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    >
                      <option value="">Unassigned</option>
                      {engineers.map((eng) => (
                        <option key={eng.user_id} value={eng.user_id}>
                          {eng.full_name} ({eng.email})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={newDueDate}
                    onChange={(e) => setNewDueDate(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {submitting ? 'Creating...' : 'Create Task'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Complete Maintenance Task */}
        {isCompleteOpen && activeTask && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-100">
              <h2 className="text-lg font-bold text-slate-800 mb-2">Complete Task #{activeTask.task_id}</h2>
              <p className="text-xs text-slate-500 mb-4">{activeTask.title}</p>
              <form onSubmit={handleCompleteSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Resolution Notes & Actions Taken
                  </label>
                  <textarea
                    value={completionNotes}
                    onChange={(e) => setCompletionNotes(e.target.value)}
                    placeholder="Describe repair actions, materials used, and observations..."
                    rows={4}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                    required
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCompleteOpen(false)
                      setActiveTask(null)
                    }}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {submitting ? 'Submitting...' : 'Mark Completed'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Verify Maintenance Task */}
        {isVerifyOpen && activeTask && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-100">
              <h2 className="text-lg font-bold text-slate-800 mb-2">Engineering Verification</h2>
              <p className="text-xs text-slate-500 mb-3">
                Review work completed for task #{activeTask.task_id}: {activeTask.title}
              </p>

              {activeTask.resolution_notes && (
                <div className="mb-4 p-3 bg-slate-50 rounded-lg text-xs text-slate-700 border border-slate-200">
                  <span className="font-bold text-slate-500 block mb-1">Technician Notes:</span>
                  {activeTask.resolution_notes}
                </div>
              )}

              <form onSubmit={handleVerifySubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-2">Decision</label>
                  <div className="flex space-x-4">
                    <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="radio"
                        checked={verifyApproved}
                        onChange={() => setVerifyApproved(true)}
                        className="text-indigo-600"
                      />
                      <span className="font-semibold text-emerald-700">Approve & Verify</span>
                    </label>
                    <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="radio"
                        checked={!verifyApproved}
                        onChange={() => setVerifyApproved(false)}
                        className="text-indigo-600"
                      />
                      <span className="font-semibold text-rose-700">Reopen for Revision</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    {verifyApproved ? 'Verification Comment (Optional)' : 'Reason for Reopening (Required)'}
                  </label>
                  <textarea
                    value={verifyComment}
                    onChange={(e) => setVerifyComment(e.target.value)}
                    placeholder={verifyApproved ? 'Looks good, approved for closure.' : 'Explain what additional repair work is required...'}
                    rows={3}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                    required={!verifyApproved}
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => {
                      setIsVerifyOpen(false)
                      setActiveTask(null)
                    }}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {submitting ? 'Submitting...' : 'Confirm Decision'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
export default Maintenance
