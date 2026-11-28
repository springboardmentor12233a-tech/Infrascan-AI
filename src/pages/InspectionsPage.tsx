import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Eye,
  Search,
  Download,
  RefreshCw,
  ClipboardCheck,
  Clock,
  CheckCircle2,
  Cpu,
  AlertTriangle,
  Calendar as CalendarIcon,
  List,
  Edit2,
  Images,
  ScanSearch,
  FileText,
  XCircle,
} from 'lucide-react'
import { inspectionService } from '@/services/inspectionService'
import { INFRASTRUCTURE_TYPES } from '@/lib/constants'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { AIProcessingBadge } from '@/components/inspections/AIProcessingBadge'
import { InspectionCalendar } from '@/components/inspections/InspectionCalendar'
import { Modal } from '@/components/ui/Modal'
import { DemoBanner } from '@/components/ui/DemoBanner'
import type { Inspection } from '@/types'

export function InspectionsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: inspections = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['inspections'],
    queryFn: inspectionService.getAll,
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => inspectionService.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      setCancelTarget(null)
    },
  })

  const [viewMode, setViewMode] = useState<'table' | 'calendar'>('table')
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [aiFilter, setAiFilter] = useState('All')
  const [cancelTarget, setCancelTarget] = useState<Inspection | null>(null)

  const filtered = useMemo(() => {
    return inspections.filter((i) => {
      const matchesSearch =
        i.id.toLowerCase().includes(search.toLowerCase()) ||
        i.assetName.toLowerCase().includes(search.toLowerCase()) ||
        i.inspectorName.toLowerCase().includes(search.toLowerCase())
      const matchesType = typeFilter === 'All' || i.assetType === typeFilter
      const matchesStatus = statusFilter === 'All' || i.status === statusFilter
      const matchesAi = aiFilter === 'All' || (i.aiStatus || 'Not Started') === aiFilter
      return matchesSearch && matchesType && matchesStatus && matchesAi
    })
  }, [inspections, search, typeFilter, statusFilter, aiFilter])

  const exportCsv = () => {
    const header = 'Inspection ID,Asset,Asset ID,Type,Inspector,Date,Images,AI Status,Status\n'
    const rows = filtered
      .map(
        (i) =>
          `"${i.id}","${i.assetName}","${i.assetId}","${i.assetType}","${i.inspectorName}","${i.date}",${i.imageCount},"${i.aiStatus || 'Not Started'}","${i.status}"`
      )
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'infrascan-inspections.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Inspection Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Schedule, organize and monitor infrastructure inspections and AI-powered damage assessment activities.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex border border-slate-200 rounded-md bg-white overflow-hidden">
            <button
              onClick={() => setViewMode('table')}
              className={`px-2.5 py-2 text-xs font-medium inline-flex items-center gap-1 ${
                viewMode === 'table' ? 'bg-[#0F2942] text-white' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <List className="w-3.5 h-3.5" /> Table
            </button>
            <button
              onClick={() => setViewMode('calendar')}
              className={`px-2.5 py-2 text-xs font-medium inline-flex items-center gap-1 ${
                viewMode === 'calendar' ? 'bg-[#0F2942] text-white' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <CalendarIcon className="w-3.5 h-3.5" /> Calendar
            </button>
          </div>
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
            to="/app/inspections/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
          >
            <Plus className="w-4 h-4" /> Create Inspection
          </Link>
        </div>
      </div>

      <DemoBanner />

      {/* 6 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <DashboardCard title="Total Inspections" value={inspections.length} icon={ClipboardCheck} accent="navy" />
        <DashboardCard
          title="Scheduled"
          value={inspections.filter((i) => i.status === 'Scheduled' || i.status === 'Pending').length}
          icon={CalendarIcon}
          accent="cyan"
        />
        <DashboardCard
          title="In Progress"
          value={inspections.filter((i) => i.status === 'In Progress' || i.status === 'Processing').length}
          icon={Clock}
          accent="amber"
        />
        <DashboardCard
          title="Completed"
          value={inspections.filter((i) => i.status === 'Completed').length}
          icon={CheckCircle2}
          accent="emerald"
        />
        <DashboardCard
          title="Pending AI Analysis"
          value={inspections.filter((i) => i.aiStatus === 'Not Started' || i.aiStatus === 'Queued').length}
          icon={Cpu}
          accent="navy"
        />
        <DashboardCard
          title="Requires Review"
          value={inspections.filter((i) => i.status === 'Requires Review').length}
          icon={AlertTriangle}
          accent="red"
        />
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Inspection ID, asset, or inspector..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-md focus:outline-none focus:border-cyan-600"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Asset Types</option>
          {INFRASTRUCTURE_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Statuses</option>
          <option value="Draft">Draft</option>
          <option value="Scheduled">Scheduled</option>
          <option value="Pending">Pending</option>
          <option value="Processing">Processing</option>
          <option value="Completed">Completed</option>
          <option value="Requires Review">Requires Review</option>
          <option value="Cancelled">Cancelled</option>
        </select>
        <select
          value={aiFilter}
          onChange={(e) => setAiFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All AI Statuses</option>
          <option value="Not Started">Not Started</option>
          <option value="Queued">Queued</option>
          <option value="Processing">Processing</option>
          <option value="Completed">Completed</option>
        </select>
      </div>

      {viewMode === 'calendar' ? (
        <InspectionCalendar inspections={filtered} />
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-slate-500">Loading inspections...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-medium">Inspection ID</th>
                    <th className="px-4 py-3 font-medium">Infrastructure</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">Inspector</th>
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Images</th>
                    <th className="px-4 py-3 font-medium">AI Status</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((insp) => (
                    <tr key={insp.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono font-medium text-slate-800">
                        <Link to={`/app/inspections/${insp.id}`} className="hover:text-cyan-700 hover:underline">
                          {insp.id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900">{insp.assetName}</td>
                      <td className="px-4 py-3 text-slate-600">{insp.assetType}</td>
                      <td className="px-4 py-3 text-slate-600">{insp.inspectorName}</td>
                      <td className="px-4 py-3 text-slate-600">{insp.date}</td>
                      <td className="px-4 py-3 text-slate-600">{insp.imageCount}</td>
                      <td className="px-4 py-3">
                        <AIProcessingBadge status={insp.aiStatus} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={insp.status} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          <button
                            onClick={() => navigate(`/app/inspections/${insp.id}`)}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                            title="View Inspection"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => navigate(`/app/inspections/${insp.id}/edit`)}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                            title="Edit Inspection"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => navigate(`/app/inspections/${insp.id}/images`)}
                            className="p-1.5 rounded hover:bg-slate-100 text-cyan-700"
                            title="Upload Images"
                          >
                            <Images className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => navigate('/app/analysis')}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                            title="Run AI Analysis"
                          >
                            <ScanSearch className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => navigate('/app/reports')}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                            title="Generate Report"
                          >
                            <FileText className="w-3.5 h-3.5" />
                          </button>
                          {insp.status !== 'Cancelled' && (
                            <button
                              onClick={() => setCancelTarget(insp)}
                              className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600"
                              title="Cancel Inspection"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                            </button>
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
      )}

      {/* Cancel Confirmation Modal */}
      <Modal
        open={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        title="Cancel Inspection"
        subtitle={cancelTarget ? `${cancelTarget.id} — ${cancelTarget.assetName}` : ''}
      >
        <div className="space-y-4 text-xs">
          <p className="text-slate-600">Are you sure you want to cancel this scheduled inspection?</p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setCancelTarget(null)} className="px-4 py-2 border border-slate-200 rounded-md">
              Keep Inspection
            </button>
            <button
              onClick={() => cancelTarget && cancelMutation.mutate(cancelTarget.id)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium"
            >
              Confirm Cancel
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
