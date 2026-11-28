import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Play, Cpu, CheckCircle2 } from 'lucide-react'
import { MOCK_ASSETS, MOCK_INSPECTIONS, MOCK_IMAGES } from '@/data/mockData'
import { analysisService } from '@/services/analysisService'
import { DemoBanner } from '@/components/ui/DemoBanner'

const MODELS = [
  { id: 'yolo-crack', name: 'Crack Detection', arch: 'YOLO', desc: 'Bounding boxes & detection confidence' },
  { id: 'unet-crack', name: 'Crack Segmentation', arch: 'U-Net', desc: 'Pixel-level binary crack masks' },
  { id: 'effnet-cls', name: 'Crack Classification', arch: 'EfficientNet / ResNet', desc: 'Orientation & morphology' },
  { id: 'yolo-surf', name: 'Surface Damage Detection', arch: 'YOLO', desc: 'Spalling, corrosion & exposed rebar' },
  { id: 'segformer', name: 'Surface Segmentation', arch: 'U-Net / SegFormer', desc: 'Damaged surface region masks' },
  { id: 'severity', name: 'Severity Assessment', arch: 'Rule-Based Engine', desc: 'Preliminary engineering triage' },
]

const PIPELINES: Record<string, string[]> = {
  'Crack Analysis': ['yolo-crack', 'unet-crack', 'effnet-cls'],
  'Surface Damage Analysis': ['yolo-surf', 'segformer'],
  'Complete Damage Analysis': ['yolo-crack', 'unet-crack', 'effnet-cls', 'yolo-surf', 'severity'],
  'Custom Analysis': ['yolo-crack', 'unet-crack'],
}

export function NewAnalysisPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [assetId, setAssetId] = useState(MOCK_ASSETS[0].id)
  const [inspectionId, setInspectionId] = useState(MOCK_INSPECTIONS[0].id)
  const [imageId, setImageId] = useState(MOCK_IMAGES[0].id)
  const [pipeline, setPipeline] = useState('Complete Damage Analysis')
  const [selectedModels, setSelectedModels] = useState<string[]>(PIPELINES['Complete Damage Analysis'])

  const selectedAsset = MOCK_ASSETS.find((a) => a.id === assetId) || MOCK_ASSETS[0]
  const selectedImage = MOCK_IMAGES.find((i) => i.id === imageId) || MOCK_IMAGES[0]

  const runMutation = useMutation({
    mutationFn: () =>
      analysisService.createJob({
        imageId: selectedImage.id,
        imageName: selectedImage.filename,
        assetId: selectedAsset.id,
        assetName: selectedAsset.name,
        inspectionId,
        pipeline,
        modelsUsed: selectedModels,
      }),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['analysis-jobs'] })
      navigate(`/app/analysis/${job.id}/results`)
    },
  })

  const toggleModel = (id: string) => {
    setPipeline('Custom Analysis')
    setSelectedModels((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]))
  }

  return (
    <div className="space-y-5">
      <div>
        <Link to="/app/analysis" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to AI Analysis
        </Link>
        <h1 className="text-xl font-semibold text-slate-900">Configure New AI Analysis</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Select inspection imagery, configure computer vision pipelines, and launch demonstration inference
        </p>
      </div>

      <DemoBanner />

      <div className="grid lg:grid-cols-12 gap-5 items-start">
        {/* LEFT PANEL */}
        <div className="lg:col-span-4 bg-white rounded-lg border border-slate-200 p-4 space-y-4 text-xs">
          <h2 className="font-semibold text-slate-900 border-b border-slate-100 pb-2">1. Image & Inspection Input</h2>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Infrastructure Asset</label>
            <select value={assetId} onChange={(e) => setAssetId(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
              {MOCK_ASSETS.map((a) => (
                <option key={a.id} value={a.id}>{a.id} — {a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Inspection</label>
            <select value={inspectionId} onChange={(e) => setInspectionId(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
              {MOCK_INSPECTIONS.map((i) => (
                <option key={i.id} value={i.id}>{i.id} ({i.date})</option>
              ))}
            </select>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-medium text-slate-700">Uploaded Image</label>
              <Link to="/app/images/upload" className="text-cyan-700 hover:underline">+ Upload New</Link>
            </div>
            <select value={imageId} onChange={(e) => setImageId(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
              {MOCK_IMAGES.map((img) => (
                <option key={img.id} value={img.id}>{img.filename}</option>
              ))}
            </select>
          </div>
          <img src={selectedImage.url} alt={selectedImage.filename} className="w-full rounded border border-slate-200 aspect-video object-cover" />
          <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1 text-[11px]">
            <p><span className="text-slate-500">Resolution:</span> {selectedImage.resolution}</p>
            <p><span className="text-slate-500">Calibration:</span> {selectedImage.calibrated ? `Calibrated (${selectedImage.pxPerMm} px/mm)` : 'Not Calibrated'}</p>
          </div>
        </div>

        {/* MAIN PANEL */}
        <div className="lg:col-span-5 bg-white rounded-lg border border-slate-200 p-4 space-y-4 text-xs">
          <h2 className="font-semibold text-slate-900 border-b border-slate-100 pb-2">2. Pipeline & Model Selection</h2>
          <div className="grid grid-cols-2 gap-2">
            {Object.keys(PIPELINES).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => {
                  setPipeline(p)
                  setSelectedModels(PIPELINES[p])
                }}
                className={`p-2.5 rounded-md border text-left font-medium transition-colors ${
                  pipeline === p ? 'bg-[#0F2942] text-white border-[#0F2942]' : 'bg-slate-50 text-slate-700 border-slate-200'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          <div className="space-y-2 pt-2">
            {MODELS.map((m) => {
              const active = selectedModels.includes(m.id)
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => toggleModel(m.id)}
                  className={`w-full text-left p-3 rounded-md border flex items-center justify-between transition-colors ${
                    active ? 'border-cyan-600 bg-cyan-50/40' : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div>
                    <p className="font-semibold text-slate-900 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-cyan-700" /> {m.name}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{m.arch} · {m.desc}</p>
                  </div>
                  {active && <CheckCircle2 className="w-4 h-4 text-cyan-700 shrink-0" />}
                </button>
              )
            })}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="lg:col-span-3 bg-white rounded-lg border border-slate-200 p-4 space-y-4 text-xs">
          <h2 className="font-semibold text-slate-900 border-b border-slate-100 pb-2">3. Analysis Summary</h2>
          <div className="space-y-2">
            <div><span className="text-slate-500">Asset:</span> <p className="font-medium text-slate-900">{selectedAsset.name}</p></div>
            <div><span className="text-slate-500">Inspection:</span> <p className="font-mono font-medium">{inspectionId}</p></div>
            <div><span className="text-slate-500">Image:</span> <p className="font-mono font-medium truncate">{selectedImage.filename}</p></div>
            <div><span className="text-slate-500">Pipeline:</span> <p className="font-semibold text-cyan-800">{pipeline}</p></div>
            <div><span className="text-slate-500">Models Enabled:</span> <p className="font-semibold">{selectedModels.length} of 6</p></div>
          </div>
          <button
            type="button"
            disabled={selectedModels.length === 0 || runMutation.isPending}
            onClick={() => runMutation.mutate()}
            className="w-full py-2.5 px-4 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" /> {runMutation.isPending ? 'Submitting Job...' : 'RUN AI ANALYSIS'}
          </button>
        </div>
      </div>
    </div>
  )
}

