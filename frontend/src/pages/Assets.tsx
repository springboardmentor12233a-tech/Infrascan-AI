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

    // Basic frontend checks
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
      // Show clear 400 or 403 error message
      setError(
        err.response?.data?.detail ||
          'Error deleting asset. Inspection records may be linked.',
      )
    }
  }

  const totalPages = Math.ceil(total / pageSize) || 1

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header section */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-200 mb-6 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
              Infrastructure Assets
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Registry of bridges, roads, tunnels, and concrete structures
              monitored by InfraScan.
            </p>
          </div>
          {canManageAssets && (
            <button
              onClick={openAddModal}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
            >
              + Add Asset
            </button>
          )}
        </div>

        {/* Alerts */}
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

        {/* Filter & Search Bar */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
          <form
            onSubmit={handleSearchSubmit}
            className="grid grid-cols-1 sm:grid-cols-4 gap-4"
          >
            {/* Search Input */}
            <div className="sm:col-span-2">
              <input
                type="text"
                placeholder="Search by asset name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Asset Type Filter */}
            <div>
              <select
                value={assetType}
                onChange={(e) => {
                  setAssetType(e.target.value)
                  setPage(1)
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Types</option>
                {ASSET_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>

            {/* Material Filter */}
            <div>
              <select
                value={materialType}
                onChange={(e) => {
                  setMaterialType(e.target.value)
                  setPage(1)
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Materials</option>
                {MATERIAL_TYPES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          </form>
        </div>

        {/* Assets Table (Screen 3 style) */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-sm text-slate-500 animate-pulse">
              Loading infrastructure assets...
            </div>
          ) : assets.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500">
              No assets found matching your criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 font-semibold text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3.5">ID</th>
                    <th className="px-5 py-3.5">Name</th>
                    <th className="px-5 py-3.5">Type</th>
                    <th className="px-5 py-3.5">Location</th>
                    <th className="px-5 py-3.5">Material</th>
                    <th className="px-5 py-3.5">Last Inspection</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {assets.map((asset) => (
                    <tr key={asset.asset_id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-5 py-4 font-mono text-xs text-slate-500">
                        #{asset.asset_id}
                      </td>
                      <td className="px-5 py-4 font-medium text-indigo-600 hover:text-indigo-800">
                        <Link to={`/assets/${asset.asset_id}`}>
                          {asset.name}
                        </Link>
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-block px-2.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 capitalize">
                          {asset.asset_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-xs text-slate-600">
                        <div>
                          {asset.latitude.toFixed(4)}, {asset.longitude.toFixed(4)}
                        </div>
                        {asset.address && (
                          <div className="text-slate-400 text-[11px] truncate max-w-xs">
                            {asset.address}
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-4 capitalize text-slate-600">
                        {asset.material_type}
                      </td>
                      <td className="px-5 py-4 text-xs">
                        {asset.last_inspection_date ? (
                          <span className="text-slate-700 font-medium">
                            {new Date(asset.last_inspection_date).toLocaleDateString()}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">No records</span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-right space-x-2">
                        <Link
                          to={`/assets/${asset.asset_id}`}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                        >
                          Details
                        </Link>
                        {canManageAssets && (
                          <button
                            onClick={() => openEditModal(asset)}
                            className="text-xs text-slate-600 hover:text-slate-900 font-medium ml-2"
                          >
                            Edit
                          </button>
                        )}
                        {canDeleteAssets && (
                          <button
                            onClick={() => handleDelete(asset.asset_id)}
                            className="text-xs text-rose-600 hover:text-rose-800 font-medium ml-2"
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
          <div className="px-5 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <div>
              Showing <span className="font-medium">{assets.length}</span> of{' '}
              <span className="font-medium">{total}</span> assets
            </div>
            <div className="flex space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 bg-white border border-slate-300 rounded font-medium disabled:opacity-40"
              >
                Previous
              </button>
              <span className="py-1 px-2 font-medium text-slate-700">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-white border border-slate-300 rounded font-medium disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Add / Edit Asset Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <h2 className="text-lg font-bold text-slate-800 mb-4">
              {editingAssetId ? 'Edit Asset' : 'Add New Infrastructure Asset'}
            </h2>

            {modalError && (
              <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                {modalError}
              </div>
            )}

            <form onSubmit={handleModalSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Asset Name *
                </label>
                <input
                  type="text"
                  required
                  value={modalForm.name}
                  onChange={(e) =>
                    setModalForm({ ...modalForm, name: e.target.value })
                  }
                  placeholder="e.g. Bridge B-12"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Asset Type
                  </label>
                  <select
                    value={modalForm.asset_type}
                    onChange={(e) =>
                      setModalForm({ ...modalForm, asset_type: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    {ASSET_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
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
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    {MATERIAL_TYPES.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Address / Landmark
                </label>
                <input
                  type="text"
                  value={modalForm.address}
                  onChange={(e) =>
                    setModalForm({ ...modalForm, address: e.target.value })
                  }
                  placeholder="e.g. Kathipara Junction, Chennai"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
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
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
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
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
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
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Frequency (Days)
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
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
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
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    {IMPORTANCE_LEVELS.map((i) => (
                      <option key={i} value={i}>
                        {i}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
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
                  disabled={modalSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium shadow-sm disabled:opacity-50"
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
