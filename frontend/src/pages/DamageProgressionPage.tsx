import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { Download, AlertCircle } from 'lucide-react'
import { MOCK_ASSETS } from '@/data/mockData'
import { SAMPLE_INSPECTION_IMAGES } from '@/data/mockImages'
import { ChartCard } from '@/components/ui/ChartCard'
import { DemoBanner } from '@/components/ui/DemoBanner'

const PROGRESSION_DATA = [
  { date: '2025-05', detections: 2, lengthMm: 980 },
  { date: '2025-11', detections: 2, lengthMm: 1120 },
  { date: '2026-05', detections: 3, lengthMm: 1290 },
  { date: '2026-11', detections: 4, lengthMm: 1420 },
]

export function DamageProgressionPage() {
  const { assetId } = useParams<{ assetId: string }>()
  const [selectedAssetId, setSelectedAssetId] = useState(assetId || MOCK_ASSETS[0].id)

  const exportCsv = () => {
    const csv = 'Date,Detections,Calibrated Length (mm)\n' + PROGRESSION_DATA.map((d) => `${d.date},${d.detections},${d.lengthMm}`).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `infrascan-progression-${selectedAssetId}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Damage Progression</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Historical inspection comparison and calibrated crack growth tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedAssetId}
            onChange={(e) => setSelectedAssetId(e.target.value)}
            className="px-3 py-2 text-xs border border-slate-200 rounded-md bg-white"
          >
            {MOCK_ASSETS.map((a) => (
              <option key={a.id} value={a.id}>
                {a.id} — {a.name}
              </option>
            ))}
          </select>
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-[#0F2942] text-white text-xs font-medium hover:bg-[#163859]"
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
        </div>
      </div>

      <DemoBanner message="DEMO DATA: Historical progression figures are simulated. Image angle, lighting, occlusion, and coverage can affect detection across inspection dates." />

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="flex items-center justify-between mb-2 text-xs">
            <span className="font-semibold text-slate-700">Previous Inspection (May 2026)</span>
            <span className="font-mono text-slate-500">Est. 1290mm × 4.1mm</span>
          </div>
          <img src={SAMPLE_INSPECTION_IMAGES.bridgePierCrack} alt="Previous inspection" className="w-full rounded border border-slate-200 opacity-90" />
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="flex items-center justify-between mb-2 text-xs">
            <span className="font-semibold text-slate-900">Current Inspection (Nov 2026)</span>
            <span className="font-mono text-red-600 font-semibold">Est. 1420mm × 4.8mm</span>
          </div>
          <img src={SAMPLE_INSPECTION_IMAGES.bridgePierCrack} alt="Current inspection" className="w-full rounded border border-slate-200" />
        </div>
      </div>

      <div className="p-3 rounded-md bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>
          Note: Absence of a finding in a later image does not automatically indicate repair; camera angle, lighting, and
          occlusion may affect detection.
        </span>
      </div>

      <ChartCard title="Calibrated Crack Length Progression" subtitle="Available calibrated measurements across 4 inspection cycles">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={PROGRESSION_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="lengthMm" name="Crack Length (mm)" stroke="#0F2942" strokeWidth={2.5} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  )
}
