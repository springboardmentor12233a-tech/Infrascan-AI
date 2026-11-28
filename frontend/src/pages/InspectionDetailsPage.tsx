import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ScanSearch, FileText, UploadCloud, Cpu, UserCheck, Clock } from 'lucide-react'
import { inspectionService } from '@/services/inspectionService'
import { MOCK_IMAGES } from '@/data/mockData'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { AIProcessingBadge } from '@/components/inspections/AIProcessingBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'

type TabKey = 'overview' | 'images' | 'ai' | 'findings' | 'history'

export function InspectionDetailsPage({ initialTab = 'overview' }: { initialTab?: TabKey }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<TabKey>(initialTab)

  const { data: inspection, isLoading } = useQuery({
    queryKey: ['inspection', id],
    queryFn: () => inspectionService.getById(id!),
    enabled: Boolean(id),
  })

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading inspection workspace...</div>
  }

  if (!inspection) {
    return (
      <div className="p-8 text-center space-y-2">
        <p className="text-sm font-semibold text-slate-900">Inspection Not Found</p>
        <Link to="/app/inspections" className="text-xs text-cyan-700 hover:underline">
          Back to Inspections
        </Link>
      </div>
    )
  }

  const relatedImages = MOCK_IMAGES.filter((img) => img.inspectionId === inspection.id || img.assetId === inspection.assetId)

  return (
    <div className="space-y-5">
      <div>
        <Link to="/app/inspections" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Inspections
        </Link>
        <div className="bg-white rounded-lg border border-slate-200 p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                {inspection.id}
              </span>
              <StatusBadge status={inspection.status} />
              <AIProcessingBadge status={inspection.aiStatus} />
            </div>
            <h1 className="text-xl font-semibold text-slate-900 mt-2">
              {inspection.title || `${inspection.assetName} Inspection`}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Asset: <Link to={`/app/assets/${inspection.assetId}`} className="text-cyan-700 hover:underline">{inspection.assetName}</Link> · Inspector: {inspection.inspectorName} · Date: {inspection.date}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setTab('images')}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium"
            >
              <UploadCloud className="w-3.5 h-3.5" /> Upload Images
            </button>
            <button
              onClick={() => navigate('/app/analysis')}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
            >
              <ScanSearch className="w-3.5 h-3.5" /> Run AI Analysis
            </button>
            <button
              onClick={() => navigate('/app/reports')}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium"
            >
              <FileText className="w-3.5 h-3.5" /> Generate Report
            </button>
          </div>
        </div>
      </div>

      <DemoBanner />

      <div className="flex flex-wrap gap-1 border-b border-slate-200">
        {(
          [
            ['overview', 'Overview'],
            ['images', `Images (${relatedImages.length})`],
            ['ai', 'AI Analysis'],
            ['findings', 'Findings'],
            ['history', 'History'],
          ] as [TabKey, string][]
        ).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              tab === k ? 'border-[#0F2942] text-[#0F2942]' : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div><p className="text-slate-500">Infrastructure</p><p className="font-medium text-slate-900 mt-0.5">{inspection.assetName}</p></div>
          <div><p className="text-slate-500">Asset Type</p><p className="font-medium text-slate-900 mt-0.5">{inspection.assetType}</p></div>
          <div><p className="text-slate-500">Assigned Inspector</p><p className="font-medium text-slate-900 mt-0.5">{inspection.inspectorName}</p></div>
          <div><p className="text-slate-500">Inspection Date</p><p className="font-medium text-slate-900 mt-0.5">{inspection.date}</p></div>
          <div><p className="text-slate-500">Method</p><p className="font-medium text-slate-900 mt-0.5">{inspection.method || 'Drone & Visual Inspection'}</p></div>
          <div><p className="text-slate-500">Max Severity</p><div className="mt-0.5"><SeverityBadge severity={inspection.maxSeverity} /></div></div>
          <div className="sm:col-span-2 lg:col-span-3">
            <p className="text-slate-500">Field Notes</p>
            <p className="mt-1 p-3 rounded bg-slate-50 border border-slate-200 text-slate-700">{inspection.notes}</p>
          </div>
        </div>
      )}

      {tab === 'images' && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {relatedImages.map((img) => (
            <div key={img.id} className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <img src={img.url} alt={img.filename} className="w-full aspect-video object-cover" />
              <div className="p-3 text-xs flex items-center justify-between">
                <span className="font-mono truncate">{img.filename}</span>
                {img.severity && <SeverityBadge severity={img.severity} />}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'ai' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-slate-900">
              <Cpu className="w-4 h-4 text-cyan-700" /> AI Analysis Job (Demonstration)
            </div>
            <AIProcessingBadge status={inspection.aiStatus} />
          </div>
          <p className="text-slate-600">
            Pipeline: InfraScan-CrackNet-v2.4 (Demo) · Open the full AI Damage Analysis workspace to inspect bounding
            boxes, segmentation masks, and explainability heatmaps.
          </p>
          <Link to="/app/analysis" className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F2942] text-white rounded-md font-medium">
            <ScanSearch className="w-3.5 h-3.5" /> Open AI Analysis Workspace
          </Link>
        </div>
      )}

      {tab === 'findings' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-3 text-xs">
          <div className="p-3.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900 flex items-center gap-2">
                Longitudinal Crack <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-50 text-cyan-800 border border-cyan-200">AI Prediction (Demo)</span>
              </p>
              <p className="text-slate-500 mt-0.5">Confidence: 96% · Awaiting engineer confirmation</p>
            </div>
            <SeverityBadge severity="Critical" />
          </div>
          <div className="p-3.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900 flex items-center gap-2">
                Concrete Spalling <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200"><UserCheck className="w-3 h-3 inline mr-1" />Engineer Confirmed</span>
              </p>
              <p className="text-slate-500 mt-0.5">Confirmed by {inspection.inspectorName}</p>
            </div>
            <SeverityBadge severity="High" />
          </div>
        </div>
      )}

      {tab === 'history' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-3 text-xs">
          {[
            { event: 'Inspection Created & Scheduled', time: inspection.date },
            { event: `Assigned to ${inspection.inspectorName}`, time: inspection.date },
            { event: `${inspection.imageCount} Inspection Photographs Uploaded`, time: inspection.date },
          ].map((h, i) => (
            <div key={i} className="flex items-center gap-3 border-l-2 border-cyan-600 pl-3 py-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <div>
                <p className="font-medium text-slate-900">{h.event}</p>
                <p className="text-[11px] text-slate-500">{h.time}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

