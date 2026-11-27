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
  const [searchQuery, setSearchQuery] = useState('')
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

  const filteredInspections = inspections.filter((insp) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      insp.inspection_id.toString().includes(q) ||
      (insp.asset_name && insp.asset_name.toLowerCase().includes(q)) ||
      (insp.inspector_name && insp.inspector_name.toLowerCase().includes(q))
    )
  })

  return (
    <div className="min-h-screen bg-[#141619] text-white flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-[#2C2E3A] gap-4">
          <div>
            <div className="text-xs font-mono font-semibold text-[#0A21C0] uppercase tracking-wider mb-1">
              Field Operations & Audit
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Inspections Management
            </h1>
            <p className="text-xs sm:text-sm text-[#B3B4BD] mt-1">
              {role === 'inspector'
                ? 'Your assigned field crack inspection tasks and photographic records.'
                : 'Schedule, track, review, and analyze civil infrastructure inspection workflows.'}
            </p>
          </div>
          {canCreateInspection && (
            <button
              onClick={openNewInspectionModal}
              className="inline-flex items-center px-5 py-2.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white text-xs font-semibold rounded-full shadow-lg shadow-[#0A21C0]/30 transition-all cursor-pointer shrink-0"
            >
              + Schedule Inspection
            </button>
          )}
        </div>

        {/* Feedback alerts */}
        {success && (
          <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs sm:text-sm rounded-xl flex items-center justify-between backdrop-blur-md">
            <span>{success}</span>
            <button onClick={() => setSuccess(null)} className="text-emerald-400 hover:text-white font-bold">&times;</button>
          </div>
        )}
        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs sm:text-sm rounded-xl flex items-center justify-between backdrop-blur-md">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white font-bold">&times;</button>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 shadow-xl">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Search by ID, asset, or inspector..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-4 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-full text-xs text-white placeholder-[#B3B4BD]/50 focus:outline-none w-64"
            />

            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-[#B3B4BD]">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
              >
                <option value="">All Statuses</option>
                {STATUS_OPTIONS.map((st) => (
                  <option key={st} value={st}>
                    {st.replace('_', ' ').toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs text-[#B3B4BD]">
            <span>Showing <strong>{filteredInspections.length}</strong> inspections</span>
            <button
              onClick={fetchInspections}
              className="px-3.5 py-1.5 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-white rounded-full font-medium transition-all cursor-pointer"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Table View */}
        <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] overflow-hidden shadow-xl">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#B3B4BD] animate-pulse">
              <div className="w-8 h-8 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              Loading inspections registry...
            </div>
          ) : filteredInspections.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#B3B4BD]">
              No inspections found matching your criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-[#141619] text-left text-xs">
                <thead className="bg-[#141619]/80 text-[#B3B4BD] font-mono text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4">ID</th>
                    <th className="px-6 py-4">Asset</th>
                    <th className="px-6 py-4">Scheduled Date</th>
                    <th className="px-6 py-4">Inspector</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#141619]/60 text-white">
                  {filteredInspections.map((insp) => (
                    <tr key={insp.inspection_id} className="hover:bg-[#141619]/40 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-[#0A21C0]">
                        <Link
                          to={`/inspections/${insp.inspection_id}`}
                          className="hover:underline flex items-center space-x-1"
                        >
                          <span>#{insp.inspection_id}</span>
                        </Link>
                      </td>
                      <td className="px-6 py-4 font-semibold text-white">
                        <Link
                          to={`/assets/${insp.asset_id}`}
                          className="hover:text-blue-300 transition-colors"
                        >
                          {insp.asset_name || `Asset #${insp.asset_id}`}
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-[#B3B4BD]">
                        {new Date(insp.inspection_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-[#B3B4BD]">
                        {insp.inspector_name || `User #${insp.inspector_id}`}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            insp.status === 'completed'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : insp.status === 'in_progress'
                              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              : insp.status === 'reviewed'
                              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                              : 'bg-[#050A44] text-blue-300 border border-[#0A21C0]/30'
                          }`}
                        >
                          {insp.status.replace('_', ' ')}
                        </span>
                      </td>

                      {/* Status actions */}
                      <td className="px-6 py-4 text-right">
                        <div className="inline-flex items-center space-x-2">
                          <Link
                            to={`/inspections/${insp.inspection_id}`}
                            className="px-3.5 py-1.5 text-xs font-semibold rounded-full bg-[#0A21C0] hover:bg-[#081ba0] text-white shadow-sm shadow-[#0A21C0]/20 transition-all cursor-pointer"
                            title="Open full AI assessment workspace"
                          >
                            ⚡ Open Workspace
                          </Link>
                          {role === 'inspector' && insp.inspector_id === user?.user_id ? (
                            <div className="inline-flex space-x-1">
                              {insp.status === 'assigned' && (
                                <button
                                  onClick={() =>
                                    handleStatusChange(insp.inspection_id, 'in_progress')
                                  }
                                  className="px-3 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 cursor-pointer"
                                >
                                  Start
                                </button>
                              )}
                              {insp.status === 'in_progress' && (
                                <button
                                  onClick={() =>
                                    handleStatusChange(insp.inspection_id, 'completed')
                                  }
                                  className="px-3 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30 cursor-pointer"
                                >
                                  Complete
                                </button>
                              )}
                              {insp.status === 'completed' && (
                                <span className="text-[11px] text-[#B3B4BD] italic px-2">
                                  Awaiting Review
                                </span>
                              )}
                              {insp.status === 'reviewed' && (
                                <span className="text-[11px] text-purple-400 font-semibold px-2">
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
                              className="text-xs bg-[#141619] border border-[#2C2E3A] rounded-xl px-2.5 py-1 font-medium text-white focus:outline-none focus:border-[#0A21C0]"
                            >
                              {STATUS_OPTIONS.map((st) => (
                                <option key={st} value={st}>
                                  Set to: {st.replace('_', ' ')}
                                </option>
                              ))}
                            </select>
                          ) : null}
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
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#0A21C0]/30 shadow-2xl max-w-md w-full p-6 text-white relative">
            <h2 className="text-lg font-bold text-white mb-4">
              Schedule New Inspection
            </h2>

            {modalError && (
              <div className="mb-4 p-3 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs rounded-xl">
                {modalError}
              </div>
            )}

            <form onSubmit={handleModalSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-[#B3B4BD] mb-1">
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
                  className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                >
                  {assetsList.map((a) => (
                    <option key={a.asset_id} value={a.asset_id}>
                      {a.name} ({a.asset_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#B3B4BD] mb-1">
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
                  className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
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
                <label className="block font-medium text-[#B3B4BD] mb-1">
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
                  className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-[#141619]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-[#2C2E3A] rounded-full text-xs font-semibold text-[#B3B4BD] hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalSubmitting || inspectorsList.length === 0}
                  className="px-5 py-2 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full text-xs font-semibold shadow-md shadow-[#0A21C0]/30 disabled:opacity-50 cursor-pointer"
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

export default Inspections
