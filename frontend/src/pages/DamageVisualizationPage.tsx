import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  Layers,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Eye,
} from 'lucide-react'
import { MOCK_IMAGES, MOCK_AI_ANALYSIS, MOCK_ASSETS } from '@/data/mockData'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'

export function DamageVisualizationPage() {
  const { analysisId } = useParams<{ analysisId: string }>()
  const navigate = useNavigate()

  // Layer & viewer state
  const [selectedImageId, setSelectedImageId] = useState(MOCK_IMAGES[0].id)
  const [showBoxes, setShowBoxes] = useState(true)
  const [showMasks, setShowMasks] = useState(true)
  const [maskOpacity, setMaskOpacity] = useState(0.55)
  const [zoom, setZoom] = useState(1)
  const [selectedDetId, setSelectedDetId] = useState<string | null>(null)
  const [compareMode, setCompareMode] = useState<'single' | 'side-by-side' | 'overlay'>('single')

  // Engineer review state (preserves original AI prediction separately)
  const [reviewStatus, setReviewStatus] = useState<'Pending Review' | 'Confirmed' | 'Rejected' | 'Further Inspection'>(
    'Pending Review'
  )
  const [engineerNote, setEngineerNote] = useState('')

  const img = MOCK_IMAGES.find((i) => i.id === selectedImageId) || MOCK_IMAGES[0]
  const analysis = MOCK_AI_ANALYSIS[img.id] || MOCK_AI_ANALYSIS['IMG-401']

  const exportSummary = () => {
    const payload = {
      demoData: true,
      notice: 'AI-generated visual findings are preliminary and require verification by a qualified engineer.',
      analysisId: analysisId || analysis.id,
      assetId: img.assetId,
      assetName: img.assetName,
      inspectionId: img.inspectionId,
      imageId: img.id,
      model: `${analysis.modelName} (${analysis.modelVersion})`,
      exportedAt: new Date().toISOString(),
      aiPredictions: analysis.detections,
      engineerReview: { status: reviewStatus, note: engineerNote },
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `infrascan-visualization-${analysisId || analysis.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {analysisId ? `Visualization: ${analysisId}` : 'Damage Visualization Workspace'}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            AI-generated visual findings are preliminary and require verification by a qualified engineer.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedImageId}
            onChange={(e) => setSelectedImageId(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-200 rounded-md bg-white"
          >
            {MOCK_IMAGES.map((i) => (
              <option key={i.id} value={i.id}>
                {i.assetName} ({i.filename})
              </option>
            ))}
          </select>
          <button
            onClick={exportSummary}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#0F2942] text-white text-xs font-medium hover:bg-[#163859]"
          >
            <Download className="w-3.5 h-3.5" /> Export JSON
          </button>
        </div>
      </div>

      <DemoBanner message="DEMO DATA: AI-generated visual findings are preliminary and require verification by a qualified engineer." />

      {/* Main 3-Column Workspace */}
      <div className="grid lg:grid-cols-12 gap-5 items-start">
        {/* Layer Controls */}
        <div className="lg:col-span-3 bg-white rounded-lg border border-slate-200 p-4 space-y-4 text-xs">
          <h2 className="font-semibold text-slate-900 flex items-center gap-1.5 border-b border-slate-100 pb-2">
            <Layers className="w-4 h-4 text-cyan-700" /> Layer & View Controls
          </h2>

          <div className="space-y-2">
            <label className="flex items-center justify-between cursor-pointer">
              <span>Detection Bounding Boxes</span>
              <input type="checkbox" checked={showBoxes} onChange={(e) => setShowBoxes(e.target.checked)} />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span>Segmentation Masks</span>
              <input type="checkbox" checked={showMasks} onChange={(e) => setShowMasks(e.target.checked)} />
            </label>
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-slate-600">Mask Opacity</span>
              <span className="font-mono">{Math.round(maskOpacity * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={maskOpacity}
              onChange={(e) => setMaskOpacity(Number(e.target.value))}
              className="w-full"
            />
          </div>

          <div className="pt-2 border-t border-slate-100">
            <p className="font-medium text-slate-700 mb-1.5">Comparison Mode</p>
            <div className="grid grid-cols-3 gap-1">
              {(['single', 'side-by-side', 'overlay'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setCompareMode(m)}
                  className={`py-1.5 px-2 rounded text-[11px] font-medium border capitalize ${
                    compareMode === m ? 'bg-[#0F2942] text-white border-[#0F2942]' : 'bg-slate-50 text-slate-600 border-slate-200'
                  }`}
                >
                  {m.replace('-', ' ')}
                </button>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 space-y-1.5">
            <p className="font-medium text-slate-700">Detections ({analysis.detections.length})</p>
            {analysis.detections.map((det) => (
              <button
                key={det.id}
                onClick={() => setSelectedDetId(det.id === selectedDetId ? null : det.id)}
                className={`w-full text-left p-2 rounded border transition-colors ${
                  selectedDetId === det.id ? 'border-cyan-600 bg-cyan-50' : 'border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="flex justify-between font-medium">
                  <span>{det.label}</span>
                  <span className="font-mono text-cyan-700">{Math.round(det.confidence * 100)}%</span>
                </div>
                {img.calibrated && det.estimatedLengthMm ? (
                  <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                    {det.estimatedLengthMm}mm × {det.estimatedWidthMm}mm
                  </p>
                ) : (
                  <p className="text-[11px] text-slate-400 mt-0.5">Measured in pixels (uncalibrated)</p>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Image Viewer */}
        <div className="lg:col-span-6 bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
            <span className="font-mono font-medium text-slate-700">{img.filename}</span>
            <div className="flex items-center gap-1">
              <button onClick={() => setZoom((z) => Math.max(0.75, z - 0.25))} className="p-1 rounded hover:bg-slate-200">
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono w-10 text-center">{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom((z) => Math.min(2, z + 0.25))} className="p-1 rounded hover:bg-slate-200">
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setZoom(1)} className="p-1 rounded hover:bg-slate-200">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className={`bg-slate-950 p-4 overflow-auto min-h-[400px] ${compareMode === 'side-by-side' ? 'grid grid-cols-2 gap-3' : 'flex justify-center items-center'}`}>
            {compareMode === 'side-by-side' && (
              <div>
                <p className="text-[10px] text-slate-400 mb-1 font-mono">ORIGINAL</p>
                <img src={img.url} alt="Original" className="w-full rounded" />
              </div>
            )}
            <div className="relative inline-block transition-transform" style={{ transform: `scale(${zoom})` }}>
              {compareMode === 'side-by-side' && <p className="text-[10px] text-cyan-400 mb-1 font-mono">AI OVERLAY (DEMO)</p>}
              <img src={img.url} alt={img.filename} className="max-w-full max-h-[440px] rounded block" />
              {showMasks && (
                <svg viewBox="0 0 1000 700" className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none">
                  {analysis.segmentations.map((seg) => (
                    <polygon key={seg.id} points={seg.points} fill={seg.color} fillOpacity={maskOpacity} />
                  ))}
                </svg>
              )}
              {showBoxes &&
                analysis.detections.map((det) => (
                  <div
                    key={det.id}
                    onClick={() => setSelectedDetId(det.id)}
                    style={{ left: `${det.x}%`, top: `${det.y}%`, width: `${det.width}%`, height: `${det.height}%` }}
                    className={`absolute border-2 cursor-pointer ${
                      selectedDetId === det.id ? 'border-cyan-400 bg-cyan-400/15' : 'border-red-500 bg-red-500/10'
                    }`}
                  >
                    <span className="bg-red-600 text-white text-[10px] font-mono px-1">
                      {det.label} {Math.round(det.confidence * 100)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* Engineer Review & Metadata */}
        <div className="lg:col-span-3 bg-white rounded-lg border border-slate-200 p-4 space-y-4 text-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h2 className="font-semibold text-slate-900">Engineer Review</h2>
            <SeverityBadge severity={analysis.overallSeverity} />
          </div>

          <div className="space-y-1.5 text-[11px] bg-slate-50 p-2.5 rounded border border-slate-200">
            <p><span className="text-slate-500">Asset:</span> <Link to={`/app/assets/${img.assetId}`} className="text-cyan-700 hover:underline">{img.assetName}</Link></p>
            <p><span className="text-slate-500">Inspection:</span> <Link to={`/app/inspections/${img.inspectionId}`} className="font-mono text-cyan-700 hover:underline">{img.inspectionId}</Link></p>
            <p><span className="text-slate-500">Review Status:</span> <span className="font-semibold">{reviewStatus}</span></p>
          </div>

          <div className="space-y-2">
            <p className="font-medium text-slate-700">Review Decision</p>
            <div className="grid grid-cols-2 gap-1.5">
              <button
                onClick={() => setReviewStatus('Confirmed')}
                className="inline-flex items-center justify-center gap-1 py-1.5 px-2 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 font-medium"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Confirm
              </button>
              <button
                onClick={() => setReviewStatus('Rejected')}
                className="inline-flex items-center justify-center gap-1 py-1.5 px-2 rounded border border-red-200 bg-red-50 text-red-800 hover:bg-red-100 font-medium"
              >
                <XCircle className="w-3.5 h-3.5" /> Reject
              </button>
            </div>
            <button
              onClick={() => setReviewStatus('Further Inspection')}
              className="w-full inline-flex items-center justify-center gap-1 py-1.5 px-2 rounded border border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 font-medium"
            >
              <AlertTriangle className="w-3.5 h-3.5" /> Mark for Further Inspection
            </button>
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">Engineering Note</label>
            <textarea
              rows={3}
              value={engineerNote}
              onChange={(e) => setEngineerNote(e.target.value)}
              placeholder="Add verification comments..."
              className="w-full px-2.5 py-2 border border-slate-300 rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Recent Visualizations Table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
        <div className="px-5 py-3.5 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">Recent Visualizations</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-2.5 font-medium">Asset</th>
                <th className="px-4 py-2.5 font-medium">Inspection</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {MOCK_ASSETS.slice(0, 4).map((a) => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-medium text-slate-900">{a.name}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-600">{a.lastInspectionDate}</td>
                  <td className="px-4 py-2.5"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => navigate(`/app/visualization/ANA-9001`)}
                      className="inline-flex items-center gap-1 text-cyan-700 hover:underline font-medium"
                    >
                      <Eye className="w-3.5 h-3.5" /> Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
