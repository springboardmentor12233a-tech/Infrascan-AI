import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { assetsApi, type AssetDetail } from '../api/client'

export const AssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [asset, setAsset] = useState<AssetDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    const fetchDetail = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await assetsApi.getById(parseInt(id, 10))
        setAsset(data)
      } catch (err: any) {
        setError(
          err.response?.data?.detail || 'Failed to load asset details.',
        )
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [id])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <Link
            to="/assets"
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>&larr;</span>
            <span>Back to Infrastructure Assets</span>
          </Link>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center text-sm text-slate-500 animate-pulse">
            Loading asset and inspection history...
          </div>
        ) : !asset ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center text-sm text-slate-500">
            Asset not found.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Asset Header Info */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-3">
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                      {asset.name}
                    </h1>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      #{asset.asset_id}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 mt-1">
                    {asset.address || 'No street address specified'}
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="px-3 py-1 rounded-full text-xs font-semibold uppercase bg-indigo-50 text-indigo-700">
                    {asset.asset_type.replace('_', ' ')}
                  </span>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${
                      asset.importance_level === 'high'
                        ? 'bg-rose-50 text-rose-700'
                        : asset.importance_level === 'medium'
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {asset.importance_level} priority
                  </span>
                </div>
              </div>

              {/* Attributes Grid */}
              <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-1">Material</span>
                  <span className="font-semibold text-slate-700 capitalize">
                    {asset.material_type}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-1">Coordinates</span>
                  <span className="font-semibold text-slate-700">
                    {asset.latitude.toFixed(4)}, {asset.longitude.toFixed(4)}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-1">Construction Year</span>
                  <span className="font-semibold text-slate-700">
                    {asset.construction_year}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-1">Inspection Cycle</span>
                  <span className="font-semibold text-slate-700">
                    Every {asset.inspection_frequency_days} days
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 sm:col-span-2">
                  <span className="text-slate-400 block mb-1">
                    Responsible Department
                  </span>
                  <span className="font-semibold text-slate-700">
                    {asset.responsible_department}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 sm:col-span-2">
                  <span className="text-slate-400 block mb-1">Created At</span>
                  <span className="font-semibold text-slate-700">
                    {new Date(asset.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Inspections History Section */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">
                    Inspection History
                  </h2>
                  <p className="text-xs text-slate-500">
                    All recorded structural assessments and schedules for this asset.
                  </p>
                </div>
                <Link
                  to="/inspections"
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  View All Inspections &rarr;
                </Link>
              </div>

              {asset.inspections.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
                  No inspections have been assigned or conducted for this asset yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
                      <tr>
                        <th className="px-4 py-3">ID</th>
                        <th className="px-4 py-3">Inspection Date</th>
                        <th className="px-4 py-3">Assigned Inspector</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Logged At</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {asset.inspections.map((insp) => (
                        <tr key={insp.inspection_id} className="hover:bg-slate-50/60">
                          <td className="px-4 py-3 font-mono">
                            <Link
                              to={`/inspections/${insp.inspection_id}`}
                              className="font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                            >
                              #{insp.inspection_id}
                            </Link>
                          </td>
                          <td className="px-4 py-3 font-medium text-slate-900">
                            {new Date(insp.inspection_date).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3">
                            {insp.inspector_name || `Inspector #${insp.inspector_id}`}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold capitalize ${
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
                          <td className="px-4 py-3 text-slate-400">
                            {new Date(insp.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
