import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import { assetsApi, type InfrastructureAsset } from '../api/client'

const ASSET_TYPES = [
  'building',
  'bridge',
  'road',
  'tunnel',
  'dam',
  'concrete_structure',
  'retaining_wall',
  'industrial',
]

const MATERIAL_TYPES = ['concrete', 'asphalt', 'steel', 'masonry', 'other']
const IMPORTANCE_LEVELS = ['low', 'medium', 'high']

export const Assets: React.FC = () => {
  const { role } = useAuth()
  const [assets, setAssets] = useState<InfrastructureAsset[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 8

  // Filters
  const [search, setSearch] = useState('')
  const [assetType, setAssetType] = useState('')
  const [materialType, setMaterialType] = useState('')
  const [loading, setLoading] = useState(true)

  // Feedback & error alerts
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Modal state for Add/Edit
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingAssetId, setEditingAssetId] = useState<number | null>(null)
  const [modalForm, setModalForm] = useState({
    name: '',
    asset_type: 'bridge',
    material_type: 'concrete',
    address: '',
    latitude: 13.0827,
    longitude: 80.2707,
    construction_year: 2015,
    responsible_department: 'Highways & Public Works',
    inspection_frequency_days: 90,
    importance_level: 'high',
  })
  const [modalError, setModalError] = useState<string | null>(null)
  const [modalSubmitting, setModalSubmitting] = useState(false)

  const canManageAssets = role === 'admin' || role === 'manager'
  const canDeleteAssets = role === 'admin'

  const fetchAssets = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await assetsApi.list({
        search: search || undefined,
        asset_type: assetType || undefined,
        material_type: materialType || undefined,
        page,
        page_size: pageSize,
      })
      setAssets(data.items)
      setTotal(data.total)
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Failed to retrieve infrastructure assets.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAssets()
  }, [page, assetType, materialType])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchAssets()
  }

  const openAddModal = () => {
    setEditingAssetId(null)
    setModalForm({
      name: '',
      asset_type: 'bridge',
      material_type: 'concrete',
      address: '',
      latitude: 13.0827,
      longitude: 80.2707,
      construction_year: 2015,
      responsible_department: 'Highways & Public Works',
      inspection_frequency_days: 90,
      importance_level: 'high',
    })
    setModalError(null)
    setIsModalOpen(true)
  }

  const openEditModal = (asset: InfrastructureAsset) => {
    setEditingAssetId(asset.asset_id)
    setModalForm({
      name: asset.name,
      asset_type: asset.asset_type,
      material_type: asset.material_type,
      address: asset.address || '',
      latitude: asset.latitude,
      longitude: asset.longitude,
      construction_year: asset.construction_year,
      responsible_department: asset.responsible_department,
      inspection_frequency_days: asset.inspection_frequency_days,
      importance_level: asset.importance_level,
    })
    setModalError(null)
    setIsModalOpen(true)
  }

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setModalError(null)

    if (!modalForm.name.trim()) {
      setModalError('Asset name is required.')
      return
    }
    if (modalForm.latitude < -90 || modalForm.latitude > 90) {
      setModalError('Latitude must be between -90 and 90.')
      return
    }
    if (modalForm.longitude < -180 || modalForm.longitude > 180) {
      setModalError('Longitude must be between -180 and 180.')
      return
    }
    const currentYear = new Date().getFullYear()
    if (
      modalForm.construction_year < 1800 ||
      modalForm.construction_year > currentYear
    ) {
      setModalError(`Construction year must be between 1800 and ${currentYear}.`)
      return
    }

    try {
      setModalSubmitting(true)
      if (editingAssetId) {
        await assetsApi.update(editingAssetId, modalForm)
        setSuccess(`Asset #${editingAssetId} updated successfully.`)
      } else {
        await assetsApi.create(modalForm)
        setSuccess('New asset created successfully.')
      }
      setIsModalOpen(false)
      fetchAssets()
    } catch (err: any) {
      setModalError(
        err.response?.data?.detail ||
          'Failed to save asset. Please verify input fields.',
      )
    } finally {
      setModalSubmitting(false)
    }
  }

  const handleDelete = async (assetId: number) => {
    if (!window.confirm(`Are you sure you want to delete asset #${assetId}?`)) {
      return
    }
    try {
      setError(null)
      setSuccess(null)
      await assetsApi.delete(assetId)
      setSuccess(`Asset #${assetId} deleted successfully.`)
      fetchAssets()
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Error deleting asset. Inspection records may be linked.',
      )
    }
  }

  const totalPages = Math.ceil(total / pageSize) || 1

  return (
    <div className="min-h-screen bg-[#141619] text-white flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header section */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-[#2C2E3A] gap-4">
          <div>
            <div className="text-xs font-mono font-semibold text-[#0A21C0] uppercase tracking-wider mb-1">
              Geospatial Inventory
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Infrastructure Assets
            </h1>
            <p className="text-xs sm:text-sm text-[#B3B4BD] mt-1">
              Registry of bridges, roads, tunnels, dams, and concrete structures monitored by InfraScan.
            </p>
          </div>
          {canManageAssets && (
            <button
              onClick={openAddModal}
              className="inline-flex items-center px-5 py-2.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white text-xs font-semibold rounded-full shadow-lg shadow-[#0A21C0]/30 transition-all cursor-pointer shrink-0"
            >
              + Add Infrastructure Asset
            </button>
          )}
        </div>

        {/* Alerts */}
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

        {/* Filter & Search Toolbar */}
        <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-4 shadow-xl">
          <form
            onSubmit={handleSearchSubmit}
            className="grid grid-cols-1 sm:grid-cols-4 gap-4"
          >
            <div className="sm:col-span-2">
              <input
                type="text"
                placeholder="Search by asset name or address..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full px-4 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white placeholder-[#B3B4BD]/50 focus:outline-none"
              />
            </div>

            <div>
              <select
                value={assetType}
                onChange={(e) => {
                  setAssetType(e.target.value)
                  setPage(1)
                }}
                className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
              >
                <option value="">All Asset Types</option>
                {ASSET_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace('_', ' ').toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <select
                value={materialType}
                onChange={(e) => {
                  setMaterialType(e.target.value)
                  setPage(1)
                }}
                className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
              >
                <option value="">All Materials</option>
                {MATERIAL_TYPES.map((m) => (
                  <option key={m} value={m}>
                    {m.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </form>
        </div>

        {/* Assets Table */}
        <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] overflow-hidden shadow-xl">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#B3B4BD] animate-pulse">
              <div className="w-8 h-8 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              Loading infrastructure assets...
            </div>
          ) : assets.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#B3B4BD]">
              No infrastructure assets match your filter criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-[#141619] text-left text-xs">
                <thead className="bg-[#141619]/80 text-[#B3B4BD] font-mono text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4">ID</th>
                    <th className="px-6 py-4">Asset Name</th>
                    <th className="px-6 py-4">Structure Type</th>
                    <th className="px-6 py-4">Coordinates & Location</th>
                    <th className="px-6 py-4">Material</th>
                    <th className="px-6 py-4">Importance</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#141619]/60 text-white">
                  {assets.map((asset) => (
                    <tr key={asset.asset_id} className="hover:bg-[#141619]/40 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-[#0A21C0]">
                        #{asset.asset_id}
                      </td>
                      <td className="px-6 py-4 font-semibold text-white">
                        <Link
                          to={`/assets/${asset.asset_id}`}
                          className="hover:text-blue-300 transition-colors"
                        >
                          {asset.name}
                        </Link>
                      </td>
                      <td className="px-6 py-4 capitalize">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#050A44] text-blue-300 border border-[#0A21C0]/30">
                          {asset.asset_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-[#B3B4BD]">
                        <div>
                          {asset.latitude.toFixed(4)}, {asset.longitude.toFixed(4)}
                        </div>
                        {asset.address && (
                          <div className="text-[10px] text-[#B3B4BD]/60 truncate max-w-xs mt-0.5">
                            {asset.address}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 capitalize text-[#B3B4BD]">
                        {asset.material_type}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            asset.importance_level === 'high'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : asset.importance_level === 'medium'
                              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {asset.importance_level}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <Link
                          to={`/assets/${asset.asset_id}`}
                          className="px-3 py-1 bg-[#0A21C0]/30 hover:bg-[#0A21C0] text-blue-300 hover:text-white rounded-full text-xs font-semibold transition-all inline-block"
                        >
                          Details
                        </Link>
                        {canManageAssets && (
                          <button
                            onClick={() => openEditModal(asset)}
                            className="px-3 py-1 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-[#B3B4BD] hover:text-white rounded-full text-xs font-semibold transition-all cursor-pointer"
                          >
                            Edit
                          </button>
                        )}
                        {canDeleteAssets && (
                          <button
                            onClick={() => handleDelete(asset.asset_id)}
                            className="px-3 py-1 bg-rose-950/40 hover:bg-rose-900 border border-rose-500/30 text-rose-300 hover:text-white rounded-full text-xs font-semibold transition-all cursor-pointer"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination bar */}
          <div className="px-6 py-4 bg-[#141619]/90 border-t border-[#141619] flex items-center justify-between text-xs text-[#B3B4BD]">
            <div>
              Showing <span className="font-semibold text-white">{assets.length}</span> of{' '}
              <span className="font-semibold text-white">{total}</span> assets
            </div>
            <div className="flex space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 bg-[#2C2E3A] hover:bg-[#393b4a] border border-[#2C2E3A] rounded-full font-medium text-white disabled:opacity-40 cursor-pointer"
              >
                Previous
              </button>
              <span className="py-1 px-3 font-semibold text-white">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-[#2C2E3A] hover:bg-[#393b4a] border border-[#2C2E3A] rounded-full font-medium text-white disabled:opacity-40 cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Add / Edit Asset Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#0A21C0]/30 shadow-2xl max-w-lg w-full p-6 text-white relative">
            <h2 className="text-lg font-bold text-white mb-4">
              {editingAssetId ? 'Edit Asset' : 'Add New Infrastructure Asset'}
            </h2>

            {modalError && (
              <div className="mb-4 p-3 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs rounded-xl">
                {modalError}
              </div>
            )}

            <form onSubmit={handleModalSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-[#B3B4BD] mb-1">
                  Asset Name *
                </label>
                <input
                  type="text"
                  required
                  value={modalForm.name}
                  onChange={(e) =>
                    setModalForm({ ...modalForm, name: e.target.value })
                  }
                  placeholder="e.g. Kathipara Flyover Span B"
                  className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Asset Type
                  </label>
                  <select
                    value={modalForm.asset_type}
                    onChange={(e) =>
                      setModalForm({ ...modalForm, asset_type: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  >
                    {ASSET_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.replace('_', ' ').toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Material Type
                  </label>
                  <select
                    value={modalForm.material_type}
                    onChange={(e) =>
                      setModalForm({
                        ...modalForm,
                        material_type: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  >
                    {MATERIAL_TYPES.map((m) => (
                      <option key={m} value={m}>
                        {m.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-[#B3B4BD] mb-1">
                  Address / Location Description
                </label>
                <input
                  type="text"
                  value={modalForm.address}
                  onChange={(e) =>
                    setModalForm({ ...modalForm, address: e.target.value })
                  }
                  placeholder="e.g. GST Road, Guindy, Chennai"
                  className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Latitude (-90 to 90) *
                  </label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={modalForm.latitude}
                    onChange={(e) =>
                      setModalForm({
                        ...modalForm,
                        latitude: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  />
                </div>
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Longitude (-180 to 180) *
                  </label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={modalForm.longitude}
                    onChange={(e) =>
                      setModalForm({
                        ...modalForm,
                        longitude: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Year Built *
                  </label>
                  <input
                    type="number"
                    required
                    value={modalForm.construction_year}
                    onChange={(e) =>
                      setModalForm({
                        ...modalForm,
                        construction_year: parseInt(e.target.value, 10) || 0,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  />
                </div>
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Cycle (Days)
                  </label>
                  <input
                    type="number"
                    required
                    value={modalForm.inspection_frequency_days}
                    onChange={(e) =>
                      setModalForm({
                        ...modalForm,
                        inspection_frequency_days:
                          parseInt(e.target.value, 10) || 30,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  />
                </div>
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Importance
                  </label>
                  <select
                    value={modalForm.importance_level}
                    onChange={(e) =>
                      setModalForm({
                        ...modalForm,
                        importance_level: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                  >
                    {IMPORTANCE_LEVELS.map((i) => (
                      <option key={i} value={i}>
                        {i.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-[#B3B4BD] mb-1">
                  Responsible Department *
                </label>
                <input
                  type="text"
                  required
                  value={modalForm.responsible_department}
                  onChange={(e) =>
                    setModalForm({
                      ...modalForm,
                      responsible_department: e.target.value,
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
                  disabled={modalSubmitting}
                  className="px-5 py-2 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full text-xs font-semibold shadow-md shadow-[#0A21C0]/30 disabled:opacity-50 cursor-pointer"
                >
                  {modalSubmitting ? 'Saving...' : 'Save Asset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Assets
