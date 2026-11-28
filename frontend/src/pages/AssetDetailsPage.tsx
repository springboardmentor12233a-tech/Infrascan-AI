import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import L from 'leaflet'
import { ArrowLeft, Edit2, ClipboardCheck, MapPin, Cpu, UserCheck } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { infrastructureService } from '@/services/infrastructureService'
import { MOCK_INSPECTIONS, MOCK_MAINTENANCE_TASKS } from '@/data/mockData'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { AssetConditionBadge } from '@/components/assets/AssetConditionBadge'
import { AssetStatusBadge } from '@/components/assets/AssetStatusBadge'
import { ChartCard } from '@/components/ui/ChartCard'
import { DemoBanner } from '@/components/ui/DemoBanner'

type DetailTab = 'overview' | 'inspections' | 'damage' | 'maintenance' | 'location'

const CONDITION_TREND = [
  { cycle: '2025 Q2', score: 78 },
  { cycle: '2025 Q4', score: 72 },
  { cycle: '2026 Q2', score: 64 },
  { cycle: '2026 Q4', score: 54 },
]

export function AssetDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<DetailTab>('overview')
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)

  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => infrastructureService.getById(id!),
    enabled: Boolean(id),
  })

  useEffect(() => {
    if (tab !== 'location' || !asset || !mapRef.current) return
    if (mapInstance.current) {
      mapInstance.current.remove()
      mapInstance.current = null
    }
    const map = L.map(mapRef.current).setView(asset.coordinates, 14)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
    }).addTo(map)
    L.circleMarker(asset.coordinates, {
      radius: 10,
      fillColor: '#0891B2',
      color: '#FFFFFF',
      weight: 2,
      fillOpacity: 0.9,
    }).addTo(map)
    mapInstance.current = map
    return () => {
      map.remove()
      mapInstance.current = null
    }
  }, [tab, asset])

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading infrastructure details...</div>
  }

  if (!asset) {
    return (
      <div className="p-8 text-center space-y-3">
        <p className="text-sm font-semibold text-slate-900">Infrastructure Asset Not Found</p>
        <Link to="/app/assets" className="text-xs text-cyan-700 hover:underline">
          Return to Asset Registry
        </Link>
      </div>
    )
  }

  const assetInspections = MOCK_INSPECTIONS.filter((i) => i.assetId === asset.id)
  const assetMaintenance = MOCK_MAINTENANCE_TASKS.filter((m) => m.assetId === asset.id)

  return (
    <div className="space-y-5">
      <div>
        <Link to="/app/assets" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Asset Registry
        </Link>

        {/* Header */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                {asset.id}
              </span>
              <span className="text-xs text-slate-500">{asset.type}</span>
              <AssetConditionBadge condition={asset.condition || 'Moderate Damage'} />
              <AssetStatusBadge status={asset.operationalStatus || 'Active'} />
            </div>
            <h1 className="text-xl font-semibold text-slate-900 mt-2">{asset.name}</h1>
            <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> {asset.location}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => navigate(`/app/assets/${asset.id}/edit`)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700"
            >
              <Edit2 className="w-3.5 h-3.5" /> Edit Asset
            </button>
            <button
              onClick={() => navigate('/app/inspections')}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
            >
              <ClipboardCheck className="w-3.5 h-3.5" /> Create Inspection
            </button>
          </div>
        </div>
      </div>

      <DemoBanner />

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-slate-200">
        {(
          [
            ['overview', 'Overview'],
            ['inspections', 'Inspection History'],
            ['damage', 'Damage History'],
            ['maintenance', 'Maintenance'],
            ['location', 'Location'],
          ] as [DetailTab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-[#0F2942] text-[#0F2942]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'overview' && (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 p-5 grid sm:grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-slate-500">Primary Material</p>
              <p className="font-medium text-slate-900 mt-0.5">{asset.materialType}</p>
            </div>
            <div>
              <p className="text-slate-500">Construction Year</p>
              <p className="font-medium text-slate-900 mt-0.5">{asset.constructionYear}</p>
            </div>
            <div>
              <p className="text-slate-500">Responsible Department</p>
              <p className="font-medium text-slate-900 mt-0.5">{asset.responsibleDepartment}</p>
            </div>
            <div>
              <p className="text-slate-500">Inspection Frequency</p>
              <p className="font-medium text-slate-900 mt-0.5">{asset.inspectionFrequency}</p>
            </div>
            <div>
              <p className="text-slate-500">Last Inspection</p>
              <p className="font-medium text-slate-900 mt-0.5">{asset.lastInspectionDate}</p>
            </div>
            <div>
              <p className="text-slate-500">Condition Score</p>
              <p className="font-mono font-semibold text-slate-900 mt-0.5">{asset.conditionScore}/100</p>
            </div>
          </div>

          <ChartCard title="Historical Condition Trend" subtitle="Demo condition score over cycles">
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={CONDITION_TREND}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="cycle" tick={{ fontSize: 11 }} />
                  <YAxis domain={[40, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#0891B2" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>
      )}

      {tab === 'inspections' && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">Inspection ID</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Inspector</th>
                <th className="px-4 py-3 font-medium">Images</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Max Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {assetInspections.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                    No inspection records linked to this asset yet.
                  </td>
                </tr>
              ) : (
                assetInspections.map((i) => (
                  <tr key={i.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-medium">{i.id}</td>
                    <td className="px-4 py-3">{i.date}</td>
                    <td className="px-4 py-3">{i.inspectorName}</td>
                    <td className="px-4 py-3">{i.imageCount}</td>
                    <td className="px-4 py-3"><StatusBadge status={i.status} /></td>
                    <td className="px-4 py-3"><SeverityBadge severity={i.maxSeverity} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'damage' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-3 text-xs">
          <div className="p-3.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900">Longitudinal Crack</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-50 text-cyan-800 border border-cyan-200 text-[10px] font-medium">
                  <Cpu className="w-3 h-3" /> AI Prediction (Demo)
                </span>
              </div>
              <p className="text-slate-600">Detected 2026-11-18 · Preliminary severity flagged for engineering review.</p>
            </div>
            <SeverityBadge severity="Critical" />
          </div>
          <div className="p-3.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900">Localized Concrete Spalling</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-medium">
                  <UserCheck className="w-3 h-3" /> Engineer Reviewed
                </span>
              </div>
              <p className="text-slate-600">Verified by Elena Vance, PE · Scheduled for patch rehabilitation.</p>
            </div>
            <SeverityBadge severity="High" />
          </div>
        </div>
      )}

      {tab === 'maintenance' && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-3 text-xs">
          {assetMaintenance.length === 0 ? (
            <p className="text-slate-500">No maintenance tasks recorded for this asset.</p>
          ) : (
            assetMaintenance.map((m) => (
              <div key={m.id} className="p-3.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-900">{m.title}</p>
                  <p className="text-slate-500 mt-0.5">
                    {m.priority} · Assigned to {m.assignedTo} · Due {m.dueDate}
                  </p>
                </div>
                <StatusBadge status={m.status} />
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'location' && (
        <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-slate-800">{asset.location}</span>
            <span className="font-mono text-slate-500">
              Demo Coordinates: {asset.coordinates[0].toFixed(4)}, {asset.coordinates[1].toFixed(4)}
            </span>
          </div>
          <div ref={mapRef} className="h-80 w-full rounded-md border border-slate-200" />
        </div>
      )}
    </div>
  )
}

