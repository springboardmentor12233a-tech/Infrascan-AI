import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  LayoutGrid,
  List,
  Search,
  Trash2,
  Eye,
  UploadCloud,
  Images,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Calendar,
} from 'lucide-react'
import { imageService } from '@/services/imageService'
import { MOCK_AI_ANALYSIS } from '@/data/mockData'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { AIProcessingBadge } from '@/components/inspections/AIProcessingBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'
import { formatBytes, formatDate } from '@/lib/utils'

export function ImageRepositoryPage() {
  const queryClient = useQueryClient()
  const { data: images = [], isLoading } = useQuery({
    queryKey: ['images'],
    queryFn: imageService.getAll,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => imageService.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['images'] }),
  })

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [showDetections, setShowDetections] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [qualityFilter, setQualityFilter] = useState('All')

  const filtered = useMemo(() => {
    return images.filter((img) => {
      const matchesSearch =
        img.filename.toLowerCase().includes(search.toLowerCase()) ||
        img.assetName.toLowerCase().includes(search.toLowerCase()) ||
        img.assetId.toLowerCase().includes(search.toLowerCase()) ||
        img.inspectionId.toLowerCase().includes(search.toLowerCase())
      const matchesStatus = statusFilter === 'All' || (img.processingStatus || 'Not Started') === statusFilter
      const matchesQuality = qualityFilter === 'All' || (img.qualityStatus || 'Good Quality') === qualityFilter
      return matchesSearch && matchesStatus && matchesQuality
    })
  }, [images, search, statusFilter, qualityFilter])

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Infrastructure Image Repository</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Centralized management of infrastructure inspection photographs, visual evidence and AI processing assets.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDetections((v) => !v)}
            className={`px-3 py-2 rounded-md text-xs font-medium border transition-colors ${
              showDetections
                ? 'bg-cyan-50 border-cyan-300 text-cyan-800'
                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {showDetections ? 'Marked Detections: ON' : 'Marked Detections: OFF'}
          </button>
          <div className="flex border border-slate-200 rounded-md bg-white overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-[#0F2942] text-white' : 'text-slate-600 hover:bg-slate-50'}`}
              title="Grid view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-[#0F2942] text-white' : 'text-slate-600 hover:bg-slate-50'}`}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
          <Link
            to="/app/images/upload"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] text-white text-xs font-medium hover:bg-[#163859]"
          >
            <UploadCloud className="w-4 h-4" /> Upload Images
          </Link>
        </div>
      </div>

      <DemoBanner />

      {/* 5 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <DashboardCard title="Total Images" value={images.length} icon={Images} accent="navy" />
        <DashboardCard title="Uploaded This Month" value={images.length} icon={Calendar} accent="cyan" />
        <DashboardCard
          title="Awaiting Analysis"
          value={images.filter((i) => i.processingStatus === 'Not Started' || i.processingStatus === 'Queued').length}
          icon={Clock}
          accent="amber"
        />
        <DashboardCard
          title="Processed"
          value={images.filter((i) => i.processingStatus === 'Completed').length}
          icon={CheckCircle2}
          accent="emerald"
        />
        <DashboardCard
          title="Quality Review"
          value={images.filter((i) => i.qualityStatus === 'Requires Review' || i.qualityStatus === 'Blurry').length}
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
            placeholder="Search by image name, asset ID, or inspection ID..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-md focus:outline-none focus:border-cyan-600"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Processing Statuses</option>
          <option value="Not Started">Not Started</option>
          <option value="Queued">Queued</option>
          <option value="Processing">Processing</option>
          <option value="Completed">Completed</option>
        </select>
        <select
          value={qualityFilter}
          onChange={(e) => setQualityFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
        >
          <option value="All">All Quality Statuses</option>
          <option value="Good Quality">Good Quality</option>
          <option value="Acceptable">Acceptable</option>
          <option value="Requires Review">Requires Review</option>
        </select>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-xs text-slate-500 bg-white rounded-lg border border-slate-200">
          Loading image repository...
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((img) => {
            const analysis = MOCK_AI_ANALYSIS[img.id]
            return (
            <div key={img.id} className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
              <Link to={`/app/images/${img.id}`} className="block relative aspect-video bg-slate-900 overflow-hidden">
                <img src={img.url} alt={img.filename} className="w-full h-full object-cover hover:scale-105 transition-transform" />
                {showDetections && analysis && (
                  <div className="absolute inset-0 pointer-events-none">
                    <svg viewBox="0 0 1000 700" preserveAspectRatio="none" className="w-full h-full">
                      {analysis.segmentations.map((seg) => (
                        <polygon
                          key={seg.id}
                          points={seg.points}
                          fill={seg.color}
                          fillOpacity={seg.opacity * 0.65}
                          stroke={seg.color}
                          strokeWidth="3"
                        />
                      ))}
                    </svg>
                    {analysis.detections.map((det) => (
                      <div
                        key={det.id}
                        style={{
                          left: `${det.x}%`,
                          top: `${det.y}%`,
                          width: `${det.width}%`,
                          height: `${det.height}%`,
                        }}
                        className="absolute border-2 border-red-500 bg-red-500/10"
                      >
                        <span className="absolute -top-4 left-0 bg-red-600 text-white text-[9px] font-mono px-1 py-0.5 rounded-xs whitespace-nowrap">
                          {det.label} {(det.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {img.severity && (
                  <div className="absolute top-2 right-2">
                    <SeverityBadge severity={img.severity} />
                  </div>
                )}
              </Link>
              <div className="p-3.5 space-y-2 text-xs">
                <Link to={`/app/images/${img.id}`} className="font-mono font-medium text-slate-900 hover:text-cyan-700 truncate block">
                  {img.filename}
                </Link>
                <p className="text-slate-600 truncate">{img.assetName}</p>
                <div className="flex items-center justify-between pt-1">
                  <AIProcessingBadge status={img.processingStatus} />
                  <span className="text-[11px] text-slate-500">{formatBytes(img.fileSizeBytes)}</span>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                  <Link to={`/app/images/${img.id}`} className="inline-flex items-center gap-1 text-cyan-700 hover:underline font-medium">
                    <Eye className="w-3.5 h-3.5" /> Inspect
                  </Link>
                  <button
                    onClick={() => deleteMutation.mutate(img.id)}
                    className="text-slate-400 hover:text-red-600 p-1"
                    title="Delete image"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
            )
          })}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium">Image</th>
                  <th className="px-4 py-3 font-medium">Asset</th>
                  <th className="px-4 py-3 font-medium">Inspection</th>
                  <th className="px-4 py-3 font-medium">Resolution</th>
                  <th className="px-4 py-3 font-medium">Upload Date</th>
                  <th className="px-4 py-3 font-medium">AI Status</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((img) => (
                  <tr key={img.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      <Link to={`/app/images/${img.id}`} className="hover:text-cyan-700 hover:underline">
                        {img.filename}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{img.assetName}</td>
                    <td className="px-4 py-3 font-mono text-slate-600">{img.inspectionId}</td>
                    <td className="px-4 py-3 text-slate-600">{img.resolution}</td>
                    <td className="px-4 py-3 text-slate-600">{formatDate(img.uploadDate)}</td>
                    <td className="px-4 py-3"><AIProcessingBadge status={img.processingStatus} /></td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/app/images/${img.id}`} className="text-cyan-700 hover:underline mr-3">View</Link>
                      <button onClick={() => deleteMutation.mutate(img.id)} className="text-red-600 hover:underline">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
