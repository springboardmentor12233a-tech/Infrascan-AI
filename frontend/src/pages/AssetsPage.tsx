import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Search,
  Eye,
  Edit2,
  Archive,
  Building2,
  Download,
  RefreshCw,
  ClipboardCheck,
  AlertTriangle,
  CheckCircle2,
  ArrowUpDown,
} from 'lucide-react'
import { infrastructureService } from '@/services/infrastructureService'
import { INFRASTRUCTURE_TYPES } from '@/lib/constants'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Modal } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { DemoBanner } from '@/components/ui/DemoBanner'
import type { InfrastructureAsset } from '@/types'

export function AssetsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: assets = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['assets'],
    queryFn: infrastructureService.getAll,
  })

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [materialFilter, setMaterialFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [sortBy, setSortBy] = useState<'year' | 'inspection'>('inspection')
  const [sortAsc, setSortAsc] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(5)
  const [archiveTarget, setArchiveTarget] = useState<InfrastructureAsset | null>(null)

  const archiveMutation = useMutation({
    mutationFn: (id: string) => infrastructureService.archive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      setArchiveTarget(null)
    },
  })

  const materials = useMemo(() => Array.from(new Set(assets.map((a) => a.materialType))), [assets])

  const filtered = useMemo(() => {
    const list = assets.filter((a) => {
      const matchesSearch =
        a.name.toLowerCase().includes(search.toLowerCase()) ||
        a.id.toLowerCase().includes(search.toLowerCase()) ||
        a.location.toLowerCase().includes(search.toLowerCase())
      const matchesType = typeFilter === 'All' || a.type === typeFilter
      const matchesMat = materialFilter === 'All' || a.materialType === materialFilter
      const matchesStatus = statusFilter === 'All' || a.status === statusFilter
      return matchesSearch && matchesType && matchesMat && matchesStatus
    })

    return [...list].sort((a, b) => {
      const cmp =
        sortBy === 'year'
          ? a.constructionYear - b.constructionYear
          : a.lastInspectionDate.localeCompare(b.lastInspectionDate)
      return sortAsc ? cmp : -cmp
    })
  }, [assets, search, typeFilter, materialFilter, statusFilter, sortBy, sortAsc])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize)

  const exportCsv = () => {
    const header = 'Asset ID,Name,Type,Location,Material,Year,Last Inspection,Condition,Status\n'
    const rows = filtered
      .map(
        (a) =>
          `"${a.id}","${a.name}","${a.type}","${a.location}","${a.materialType}",${a.constructionYear},"${a.lastInspectionDate}",${a.conditionScore},"${a.status}"`
      )
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'infrascan-asset-registry.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Infrastructure Asset Registry</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Register, organize and monitor infrastructure assets across your inspection portfolio.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium"
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
          <Link
            to="/app/assets/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
          >
            <Plus className="w-4 h-4" /> Register Infrastructure
          </Link>
        </div>
      </div>

      <DemoBanner />

      {/* 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DashboardCard title="Total Assets" value={assets.length} icon={Building2} accent="navy" subtitle="Registered portfolio" />
        <DashboardCard
          title="Active Assets"
          value={assets.filter((a) => a.status !== 'Archived').length}
          icon={CheckCircle2}
          accent="emerald"
          subtitle="Operational & monitored"
        />
        <DashboardCard
          title="Requiring Inspection"
          value={assets.filter((a) => a.status === 'Under Inspection' || a.status === 'Maintenance Required').length}
          icon={ClipboardCheck}
          accent="cyan"
          subtitle="Scheduled or pending"
        />
        <DashboardCard
          title="With Recorded Damage"
          value={assets.filter((a) => a.activeFindingsCount > 0).length}
          icon={AlertTriangle}
          accent="amber"
          subtitle="Active AI/field findings"
        />
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search by Asset ID, name, or location..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-md focus:outline-none focus:border-cyan-600"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value)
            setPage(1)
          }}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Types</option>
          {INFRASTRUCTURE_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={materialFilter}
          onChange={(e) => {
            setMaterialFilter(e.target.value)
            setPage(1)
          }}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Materials</option>
          {materials.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Statuses</option>
          <option value="Operational">Operational</option>
          <option value="Under Inspection">Under Inspection</option>
          <option value="Maintenance Required">Maintenance Required</option>
          <option value="Critical">Critical</option>
          <option value="Archived">Archived</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="bg-white p-8 rounded-lg border border-slate-200 text-center text-xs text-slate-500">
          Loading infrastructure registry...
        </div>
      ) : paginated.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No matching infrastructure assets"
          description="Try adjusting your search or filter criteria, or register a new asset."
        />
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium">Asset ID</th>
                  <th className="px-4 py-3 font-medium">Infrastructure Name</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Location</th>
                  <th className="px-4 py-3 font-medium">Material</th>
                  <th className="px-4 py-3 font-medium">
                    <button
                      onClick={() => {
                        setSortBy('year')
                        setSortAsc(sortBy === 'year' ? !sortAsc : false)
                      }}
                      className="inline-flex items-center gap-1 hover:text-slate-900"
                    >
                      Year <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium">
                    <button
                      onClick={() => {
                        setSortBy('inspection')
                        setSortAsc(sortBy === 'inspection' ? !sortAsc : false)
                      }}
                      className="inline-flex items-center gap-1 hover:text-slate-900"
                    >
                      Last Inspection <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="px-4 py-3 font-medium">Condition</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginated.map((asset) => (
                  <tr key={asset.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-medium text-slate-800">{asset.id}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <Link to={`/app/assets/${asset.id}`} className="hover:text-cyan-700 hover:underline">
                        {asset.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{asset.type}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.location}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.materialType}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.constructionYear}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.lastInspectionDate}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-800">{asset.conditionScore}/100</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={asset.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => navigate(`/app/assets/${asset.id}`)}
                          className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                          title="View Details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => navigate(`/app/assets/${asset.id}/edit`)}
                          className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                          title="Edit Asset"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => navigate('/app/inspections')}
                          className="p-1.5 rounded hover:bg-slate-100 text-cyan-700"
                          title="Create Inspection"
                        >
                          <ClipboardCheck className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setArchiveTarget(asset)}
                          className="p-1.5 rounded hover:bg-red-50 text-slate-500 hover:text-red-600"
                          title="Archive Asset"
                        >
                          <Archive className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination & Page Size */}
          <div className="px-4 py-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <span>Rows per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value))
                  setPage(1)
                }}
                className="px-2 py-1 border border-slate-200 rounded bg-white"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
              </select>
              <span>
                Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, filtered.length)} of {filtered.length}
              </span>
            </div>
            <div className="flex gap-1.5">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-2.5 py-1 border border-slate-200 rounded disabled:opacity-40 hover:bg-slate-50"
              >
                Prev
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 border border-slate-200 rounded disabled:opacity-40 hover:bg-slate-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      <Modal
        open={!!archiveTarget}
        onClose={() => setArchiveTarget(null)}
        title="Archive Infrastructure Asset"
        subtitle={archiveTarget ? `${archiveTarget.id} — ${archiveTarget.name}` : ''}
      >
        <div className="space-y-4 text-xs">
          <p className="text-slate-600">
            Are you sure you want to archive this infrastructure asset? Historical inspection records will be preserved.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setArchiveTarget(null)}
              className="px-4 py-2 border border-slate-200 rounded-md hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={() => archiveTarget && archiveMutation.mutate(archiveTarget.id)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium"
            >
              Confirm Archive
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
