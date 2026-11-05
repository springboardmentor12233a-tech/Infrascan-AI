import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import {
  assetsApi,
  inspectionsApi,
  usersApi,
  type InfrastructureAsset,
  type Inspection,
  type User,
} from '../api/client'

const STATUS_OPTIONS = ['assigned', 'in_progress', 'completed', 'reviewed']

export const Inspections: React.FC = () => {
  const { user, role } = useAuth()
  const [inspections, setInspections] = useState<Inspection[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)

  // Feedback alerts
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // New Inspection Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [assetsList, setAssetsList] = useState<InfrastructureAsset[]>([])
  const [inspectorsList, setInspectorsList] = useState<User[]>([])
  const [modalForm, setModalForm] = useState({
    asset_id: 0,
    inspector_id: 0,
    inspection_date: new Date().toISOString().split('T')[0],
  })
  const [modalError, setModalError] = useState<string | null>(null)
  const [modalSubmitting, setModalSubmitting] = useState(false)

  const canCreateInspection =
    role === 'admin' || role === 'manager' || role === 'civil_engineer'

  // Fetch inspections based on current user role & filter
  const fetchInspections = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await inspectionsApi.list({
        status: statusFilter || undefined,
      })
      setInspections(data)
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Failed to load inspections registry.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchInspections()
  }, [statusFilter])

  // Open modal and load asset and inspector dropdown options
  const openNewInspectionModal = async () => {
    setModalError(null)
    try {
      const [assetsData, inspectorsData] = await Promise.all([
        assetsApi.list({ page_size: 100 }),
        usersApi.getInspectors(),
      ])
      setAssetsList(assetsData.items)
      setInspectorsList(inspectorsData)

      setModalForm({
        asset_id: assetsData.items[0]?.asset_id || 0,
        inspector_id: inspectorsData[0]?.user_id || 0,
        inspection_date: new Date().toISOString().split('T')[0],
      })
      setIsModalOpen(true)
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Failed to load assets or inspectors list for scheduling.',
      )
    }
  }

  // Submit new inspection
  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setModalError(null)

    if (!modalForm.asset_id || !modalForm.inspector_id) {
      setModalError('Please select both an asset and an inspector.')
      return
    }

    try {
      setModalSubmitting(true)
      await inspectionsApi.create({
        asset_id: Number(modalForm.asset_id),
        inspector_id: Number(modalForm.inspector_id),
        inspection_date: modalForm.inspection_date,
        status: 'assigned',
      })
      setSuccess('Inspection scheduled successfully.')
      setIsModalOpen(false)
      fetchInspections()
    } catch (err: any) {
      setModalError(
        err.response?.data?.detail || 'Failed to schedule inspection.',
      )
    } finally {
      setModalSubmitting(false)
    }
  }

  // Update inspection status
  const handleStatusChange = async (inspectionId: number, newStatus: string) => {
    try {
      setError(null)
      setSuccess(null)
      await inspectionsApi.updateStatus(inspectionId, newStatus)
      setSuccess(`Inspection #${inspectionId} marked as ${newStatus.replace('_', ' ')}.`)
      fetchInspections()
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Not authorized or invalid status transition.',
      )
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-200 mb-6 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
              Inspections Management
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              {role === 'inspector'
                ? 'Your assigned field crack inspection tasks.'
                : 'Schedule, track, and review infrastructure inspection workflows.'}
            </p>
          </div>
          {canCreateInspection && (
            <button
              onClick={openNewInspectionModal}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
            >
              + New Inspection
            </button>
          )}
        </div>

        {/* Feedback alerts */}
        {success && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg flex justify-between">
            <span>{success}</span>
            <button onClick={() => setSuccess(null)} className="text-emerald-500 hover:text-emerald-800">&times;</button>
          </div>
        )}
        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg flex justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-800">&times;</button>
          </div>
        )}

        {/* Filter bar */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Filter by Status:
            </span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>
                  {st.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={fetchInspections}
            className="text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-lg bg-slate-50"
          >
            Refresh
          </button>
        </div>

        {/* Table (Screen 4 style) */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-500 animate-pulse">
              Loading inspections registry...
            </div>
          ) : inspections.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500">
              No inspections found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 font-semibold text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3.5">ID</th>
                    <th className="px-5 py-3.5">Asset</th>
                    <th className="px-5 py-3.5">Scheduled Date</th>
                    <th className="px-5 py-3.5">Assigned Inspector</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-right">Actions / Transition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {inspections.map((insp) => (
                    <tr key={insp.inspection_id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-5 py-4 font-mono text-xs">
                        <Link
                          to={`/inspections/${insp.inspection_id}`}
                          className="font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                        >
                          #{insp.inspection_id}
                        </Link>
                      </td>
                      <td className="px-5 py-4 font-medium text-indigo-600 hover:text-indigo-800">
                        <Link to={`/assets/${insp.asset_id}`}>
                          {insp.asset_name || `Asset #${insp.asset_id}`}
                        </Link>
                      </td>
                      <td className="px-5 py-4 text-xs">
                        {new Date(insp.inspection_date).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-4 text-xs text-slate-600">
                        {insp.inspector_name || `User #${insp.inspector_id}`}
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold uppercase ${
                            insp.status === 'completed'
                              ? 'bg-emerald-50 text-emerald-700'
                              : insp.status === 'in_progress'
                              ? 'bg-amber-50 text-amber-700'
                              : insp.status === 'reviewed'
                              ? 'bg-purple-50 text-purple-700'
                              : 'bg-blue-50 text-blue-700'
                          }`}
                        >
                          {insp.status.replace('_', ' ')}
                        </span>
                      </td>

                      {/* Status actions */}
                      <td className="px-5 py-4 text-right">
                        <div className="inline-flex items-center space-x-2">
                          <Link
                            to={`/inspections/${insp.inspection_id}`}
                            className="px-2.5 py-1 text-xs font-medium rounded bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100"
                            title="View inspection photos and details"
                          >
                            📷 Photos
                          </Link>
                          {role === 'inspector' && insp.inspector_id === user?.user_id ? (
                            <div className="inline-flex space-x-2">
                              {insp.status === 'assigned' && (
                                <button
                                  onClick={() =>
                                    handleStatusChange(insp.inspection_id, 'in_progress')
                                  }
                                  className="px-2.5 py-1 text-xs font-medium rounded bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100"
                                >
                                  Start Inspection
                                </button>
                              )}
                              {insp.status === 'in_progress' && (
                                <button
                                  onClick={() =>
                                    handleStatusChange(insp.inspection_id, 'completed')
                                  }
                                  className="px-2.5 py-1 text-xs font-medium rounded bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                                >
                                  Mark Completed
                                </button>
                              )}
                              {insp.status === 'completed' && (
                                <span className="text-xs text-slate-400 italic">
                                  Awaiting Review
                                </span>
                              )}
                              {insp.status === 'reviewed' && (
                                <span className="text-xs text-purple-700 font-medium">
                                  Finalized
                                </span>
                              )}
                            </div>
                          ) : canCreateInspection ? (
                            <select
                              value={insp.status}
                              onChange={(e) =>
                                handleStatusChange(insp.inspection_id, e.target.value)
                              }
                              className="text-xs border border-slate-300 rounded px-2.5 py-1 bg-white font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                            >
                              {STATUS_OPTIONS.map((st) => (
                                <option key={st} value={st}>
                                  Set to: {st.replace('_', ' ')}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <span className="text-xs text-slate-400">-</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* New Inspection Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-lg font-bold text-slate-800 mb-4">
              Schedule New Inspection
            </h2>

            {modalError && (
              <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                {modalError}
              </div>
            )}

            <form onSubmit={handleModalSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Select Infrastructure Asset *
                </label>
                <select
                  required
                  value={modalForm.asset_id}
                  onChange={(e) =>
                    setModalForm({
                      ...modalForm,
                      asset_id: parseInt(e.target.value, 10),
                    })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {assetsList.map((a) => (
                    <option key={a.asset_id} value={a.asset_id}>
                      {a.name} ({a.asset_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Assigned Inspector *
                </label>
                <select
                  required
                  value={modalForm.inspector_id}
                  onChange={(e) =>
                    setModalForm({
                      ...modalForm,
                      inspector_id: parseInt(e.target.value, 10),
                    })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {inspectorsList.length === 0 ? (
                    <option value="0">No active inspectors found</option>
                  ) : (
                    inspectorsList.map((insp) => (
                      <option key={insp.user_id} value={insp.user_id}>
                        {insp.full_name} ({insp.email})
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Inspection Date *
                </label>
                <input
                  type="date"
                  required
                  value={modalForm.inspection_date}
                  onChange={(e) =>
                    setModalForm({
                      ...modalForm,
                      inspection_date: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalSubmitting || inspectorsList.length === 0}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium shadow-sm disabled:opacity-50"
                >
                  {modalSubmitting ? 'Scheduling...' : 'Assign Inspection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
