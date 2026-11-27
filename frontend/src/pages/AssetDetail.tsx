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
    <div className="min-h-screen bg-[#141619] text-white flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="mb-2">
          <Link
            to="/assets"
            className="text-xs font-semibold text-[#B3B4BD] hover:text-white flex items-center space-x-2 transition-colors group"
          >
            <span className="text-[#0A21C0] group-hover:-translate-x-0.5 transition-transform">&larr;</span>
            <span>Back to Infrastructure Assets</span>
          </Link>
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs sm:text-sm rounded-xl">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-12 text-center text-xs text-[#B3B4BD] animate-pulse">
            <div className="w-8 h-8 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            Loading asset specifications and historical records...
          </div>
        ) : !asset ? (
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-12 text-center text-xs text-[#B3B4BD]">
            Infrastructure asset not found.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Asset Header Info */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 sm:p-8 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-80 h-80 bg-[#0A21C0]/10 rounded-full blur-3xl pointer-events-none"></div>

              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-[#141619]/60">
                <div>
                  <div className="flex items-center space-x-3">
                    <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                      {asset.name}
                    </h1>
                    <span className="font-mono text-xs px-2.5 py-1 rounded-md bg-[#050A44] text-[#0A21C0] font-bold border border-[#0A21C0]/30">
                      #{asset.asset_id}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-[#B3B4BD] mt-1">
                    {asset.address || 'Geospatial coordinates registered; no postal address logged.'}
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="px-3.5 py-1 rounded-full text-xs font-semibold uppercase bg-[#050A44] text-blue-300 border border-[#0A21C0]/40">
                    {asset.asset_type.replace('_', ' ')}
                  </span>
                  <span
                    className={`px-3.5 py-1 rounded-full text-xs font-bold uppercase ${
                      asset.importance_level === 'high'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : asset.importance_level === 'medium'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {asset.importance_level} priority
                  </span>
                </div>
              </div>

              {/* Attributes Grid */}
              <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                  <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Material Composition</span>
                  <span className="font-semibold text-white capitalize text-sm">
                    {asset.material_type}
                  </span>
                </div>

                <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                  <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">GPS Location</span>
                  <span className="font-semibold text-white font-mono text-xs">
                    {asset.latitude.toFixed(4)}, {asset.longitude.toFixed(4)}
                  </span>
                </div>

                <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                  <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Year of Erection</span>
                  <span className="font-semibold text-white text-sm">
                    {asset.construction_year}
                  </span>
                </div>

                <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A]">
                  <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Inspection Frequency</span>
                  <span className="font-semibold text-white text-sm">
                    Every {asset.inspection_frequency_days} days
                  </span>
                </div>

                <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A] sm:col-span-2">
                  <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">
                    Responsible Agency / Dept
                  </span>
                  <span className="font-semibold text-white text-sm">
                    {asset.responsible_department}
                  </span>
                </div>

                <div className="p-3 bg-[#141619] rounded-xl border border-[#2C2E3A] sm:col-span-2">
                  <span className="text-[#B3B4BD] text-[10px] uppercase font-mono block mb-1">Commission Date</span>
                  <span className="font-semibold text-white text-sm">
                    {new Date(asset.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Inspections History Section */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 sm:p-8 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-bold text-white">
                    Inspection History & Defect Audits
                  </h2>
                  <p className="text-xs text-[#B3B4BD] mt-0.5">
                    Chronological audit trails, defect logs, and AI severity records for this asset.
                  </p>
                </div>
                <Link
                  to="/inspections"
                  className="px-4 py-2 bg-[#0A21C0]/30 hover:bg-[#0A21C0] text-blue-300 hover:text-white rounded-full text-xs font-semibold transition-all"
                >
                  View All Inspections &rarr;
                </Link>
              </div>

              {asset.inspections.length === 0 ? (
                <div className="p-8 text-center text-xs text-[#B3B4BD] bg-[#141619] rounded-xl border border-dashed border-[#2C2E3A]">
                  No inspections have been conducted or scheduled for this asset yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-[#141619] text-left text-xs">
                    <thead className="bg-[#141619]/80 text-[#B3B4BD] font-mono text-[11px] uppercase tracking-wider">
                      <tr>
                        <th className="px-5 py-3.5">ID</th>
                        <th className="px-5 py-3.5">Inspection Date</th>
                        <th className="px-5 py-3.5">Inspector</th>
                        <th className="px-5 py-3.5">Status</th>
                        <th className="px-5 py-3.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#141619]/60 text-white">
                      {asset.inspections.map((insp) => (
                        <tr key={insp.inspection_id} className="hover:bg-[#141619]/40 transition-colors">
                          <td className="px-5 py-4 font-mono font-bold text-[#0A21C0]">
                            <Link
                              to={`/inspections/${insp.inspection_id}`}
                              className="hover:underline"
                            >
                              #{insp.inspection_id}
                            </Link>
                          </td>
                          <td className="px-5 py-4 text-white font-medium">
                            {new Date(insp.inspection_date).toLocaleDateString()}
                          </td>
                          <td className="px-5 py-4 text-[#B3B4BD]">
                            {insp.inspector_name || `Inspector #${insp.inspector_id}`}
                          </td>
                          <td className="px-5 py-4">
                            <span
                              className={`inline-block px-3 py-0.5 rounded-full text-[10px] font-bold uppercase ${
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
                          <td className="px-5 py-4 text-right">
                            <Link
                              to={`/inspections/${insp.inspection_id}`}
                              className="px-3.5 py-1.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full text-xs font-semibold shadow-sm transition-all"
                            >
                              ⚡ Workspace
                            </Link>
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

export default AssetDetailPage
