import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Cpu, CheckCircle2, Clock, AlertTriangle, XCircle, RotateCw, Eye } from 'lucide-react'
import { analysisService } from '@/services/analysisService'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'
import { formatDateTime } from '@/lib/utils'

export function AnalysisDashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['analysis-jobs'],
    queryFn: analysisService.getJobs,
  })

  const retryMutation = useMutation({
    mutationFn: (id: string) => analysisService.retryJob(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['analysis-jobs'] }),
  })

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  const filtered = jobs.filter((j) => {
    const matchesSearch =
      j.id.toLowerCase().includes(search.toLowerCase()) ||
      j.imageName.toLowerCase().includes(search.toLowerCase()) ||
      j.assetName.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'All' || j.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">AI Damage Analysis</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Analyze infrastructure photographs using computer vision models to detect, segment and classify visible structural damage.
          </p>
        </div>
        <Link
          to="/app/analysis/new"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
        >
          <Plus className="w-4 h-4" /> New AI Analysis
        </Link>
      </div>

      <DemoBanner />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <DashboardCard title="Total Analysis Jobs" value={jobs.length} icon={Cpu} accent="navy" />
        <DashboardCard title="Completed" value={jobs.filter((j) => j.status === 'Completed').length} icon={CheckCircle2} accent="emerald" />
        <DashboardCard title="Processing" value={jobs.filter((j) => j.status === 'Processing' || j.status === 'Queued').length} icon={Clock} accent="cyan" />
        <DashboardCard title="Failed Jobs" value={jobs.filter((j) => j.status === 'Failed').length} icon={XCircle} accent="red" />
        <DashboardCard title="Requires Review" value={jobs.filter((j) => j.status === 'Requires Review').length} icon={AlertTriangle} accent="amber" />
      </div>

      <div className="bg-white p-4 rounded-lg border border-slate-200 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Analysis ID, image, or asset..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-md focus:outline-none focus:border-cyan-600"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Statuses</option>
          <option value="Completed">Completed</option>
          <option value="Requires Review">Requires Review</option>
          <option value="Processing">Processing</option>
          <option value="Failed">Failed</option>
        </select>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading analysis jobs...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium">Analysis ID</th>
                  <th className="px-4 py-3 font-medium">Image</th>
                  <th className="px-4 py-3 font-medium">Infrastructure</th>
                  <th className="px-4 py-3 font-medium">Pipeline</th>
                  <th className="px-4 py-3 font-medium">Findings</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-medium text-slate-800">{job.id}</td>
                    <td className="px-4 py-3 font-mono text-slate-700">{job.imageName}</td>
                    <td className="px-4 py-3 text-slate-700">{job.assetName}</td>
                    <td className="px-4 py-3 text-slate-600">{job.pipeline}</td>
                    <td className="px-4 py-3 font-semibold text-slate-800">{job.findingsCount}</td>
                    <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(job.createdAt)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => navigate(`/app/analysis/${job.id}/results`)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-700"
                        >
                          <Eye className="w-3.5 h-3.5" /> Results
                        </button>
                        {job.status === 'Failed' && (
                          <button
                            onClick={() => retryMutation.mutate(job.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-cyan-200 text-cyan-700 hover:bg-cyan-50"
                          >
                            <RotateCw className="w-3.5 h-3.5" /> Retry
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
    </div>
  )
}

