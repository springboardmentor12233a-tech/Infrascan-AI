import { useState, useRef } from 'react'
import {
  UploadCloud,
  Play,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from 'lucide-react'
import { MOCK_IMAGES, MOCK_AI_ANALYSIS } from '@/data/mockData'
import { analysisService } from '@/services/analysisService'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'
import type { AiAnalysisResult } from '@/types'

type VizTab = 'original' | 'detection' | 'segmentation' | 'classification' | 'explainability'

export function AiAnalysisPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedImage, setSelectedImage] = useState({
    id: MOCK_IMAGES[0].id,
    name: MOCK_IMAGES[0].filename,
    url: MOCK_IMAGES[0].url,
    resolution: MOCK_IMAGES[0].resolution,
    calibrated: MOCK_IMAGES[0].calibrated,
  })
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [activeTab, setActiveTab] = useState<VizTab>('detection')
  const [zoom, setZoom] = useState(1)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<AiAnalysisResult>(MOCK_AI_ANALYSIS['IMG-401'])

  const handleFileChange = (file?: File) => {
    if (!file) return
    const objectUrl = URL.createObjectURL(file)
    setUploadedFile(file)
    setSelectedImage({
      id: `UPLOAD-${Date.now()}`,
      name: file.name,
      url: objectUrl,
      resolution: 'Uploaded Image',
      calibrated: false,
    })
    setError('')
  }

  const runAnalysis = async () => {
    try {
      setIsAnalyzing(true)
      setError('')
      if (uploadedFile) {
        const live = await analysisService.inferUploadedFile(uploadedFile)
        if (live.model_status === 'weights_unavailable') {
          setError(
            `AI model unavailable — model training or configuration required. (Image Quality: ${live.quality.width}×${live.quality.height}, ${live.quality.quality_status}, Blur: ${live.quality.blur_variance})`
          )
          return
        }
        setResult({
          id: `LIVE-${Date.now()}`,
          imageId: selectedImage.id,
          imageName: selectedImage.name,
          modelName: live.model_name,
          modelVersion: 'live',
          inferenceTimeMs: live.inference_time_ms,
          isDemoData: true,
          overallSeverity: 'Moderate',
          confidenceMean:
            live.detections.length > 0
              ? live.detections.reduce((s, d) => s + d.confidence, 0) / live.detections.length
              : 0,
          calibrated: false,
          detections: live.detections.map((d) => ({
            id: d.id,
            label: d.label as AiAnalysisResult['detections'][number]['label'],
            confidence: d.confidence,
            x: d.bbox_pct.x,
            y: d.bbox_pct.y,
            width: d.bbox_pct.width,
            height: d.bbox_pct.height,
            severity: 'Moderate',
          })),
          segmentations: [],
          summary: `${live.severity.severity}. ${live.severity.disclaimer}`,
          recommendations: [live.severity.disclaimer],
          analyzedAt: new Date().toISOString(),
        })
        setActiveTab('detection')
        return
      }
      const res = await analysisService.analyzeImage(selectedImage.id, selectedImage.name)
      setResult(res)
      setActiveTab('detection')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run AI analysis. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">AI Damage Analysis Workspace</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated crack detection, pixel segmentation, and severity assessment
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
          <AlertTriangle className="w-3.5 h-3.5" /> Demonstration Mode (Simulated ML Output)
        </span>
      </div>

      <DemoBanner message="Demonstration Data: Bounding boxes, segmentation masks, and crack measurements are simulated frontend data. Connect your FastAPI + PyTorch inference endpoint in .env for live predictions." />

      <div className="grid lg:grid-cols-12 gap-5 items-start">
        {/* LEFT PANEL: Upload & Sample Selector */}
        <div className="lg:col-span-3 bg-white rounded-lg border border-slate-200 p-4 space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Input Imagery</h2>

          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              handleFileChange(e.dataTransfer.files?.[0])
            }}
            className="border-2 border-dashed border-slate-300 hover:border-cyan-600 rounded-lg p-5 text-center cursor-pointer transition-colors bg-slate-50/70"
          >
            <UploadCloud className="w-7 h-7 text-cyan-700 mx-auto mb-2" />
            <p className="text-xs font-medium text-slate-800">Drop inspection image here</p>
            <p className="text-[11px] text-slate-500 mt-1">JPG, PNG, TIFF (Max 25MB)</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0])}
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1.5">Or select sample asset image:</label>
            <select
              value={selectedImage.id}
              onChange={(e) => {
                const found = MOCK_IMAGES.find((m) => m.id === e.target.value)
                if (found) {
                  setSelectedImage({
                    id: found.id,
                    name: found.filename,
                    url: found.url,
                    resolution: found.resolution,
                    calibrated: found.calibrated,
                  })
                }
              }}
              className="w-full px-2.5 py-2 text-xs border border-slate-200 rounded-md bg-white"
            >
              {MOCK_IMAGES.map((img) => (
                <option key={img.id} value={img.id}>
                  {img.filename}
                </option>
              ))}
            </select>
          </div>

          <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-xs space-y-1.5">
            <p className="font-mono font-medium text-slate-800 truncate">{selectedImage.name}</p>
            <p className="text-[11px] text-slate-500">Resolution: {selectedImage.resolution}</p>
            <p className="text-[11px] text-slate-500">
              Calibration: {selectedImage.calibrated ? 'Calibrated (mm)' : 'Uncalibrated'}
            </p>
          </div>

          <button
            onClick={runAnalysis}
            disabled={isAnalyzing}
            className="w-full py-2.5 px-4 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-60"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Running Inference...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" /> Start AI Analysis
              </>
            )}
          </button>
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>

        {/* MAIN PANEL: Visualization Canvas */}
        <div className="lg:col-span-6 bg-white rounded-lg border border-slate-200 overflow-hidden">
          {/* Tabs & Zoom Controls */}
          <div className="px-4 py-2.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2 bg-slate-50">
            <div className="flex flex-wrap gap-1">
              {(
                [
                  ['original', 'Original Image'],
                  ['detection', 'Crack Detection'],
                  ['segmentation', 'Segmentation Mask'],
                  ['classification', 'Damage Classification'],
                  ['explainability', 'Explainability'],
                ] as [VizTab, string][]
              ).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                    activeTab === key
                      ? 'bg-[#0F2942] text-white'
                      : 'text-slate-600 hover:bg-slate-200/70'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setZoom((z) => Math.max(0.75, z - 0.25))}
                className="p-1.5 rounded hover:bg-slate-200 text-slate-600"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] font-mono text-slate-600 w-10 text-center">{Math.round(zoom * 100)}%</span>
              <button
                onClick={() => setZoom((z) => Math.min(2, z + 0.25))}
                className="p-1.5 rounded hover:bg-slate-200 text-slate-600"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoom(1)}
                className="p-1.5 rounded hover:bg-slate-200 text-slate-600"
                title="Reset Zoom"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Image Viewport */}
          <div className="relative bg-slate-950 min-h-[420px] flex items-center justify-center overflow-auto p-4">
            {isAnalyzing && (
              <div className="absolute inset-0 z-20 bg-slate-950/75 flex flex-col items-center justify-center text-white text-xs gap-2">
                <Loader2 className="w-7 h-7 animate-spin text-cyan-400" />
                <span>Running InfraScan-CrackNet-v2.4 (Demo)...</span>
              </div>
            )}

            <div className="relative inline-block transition-transform duration-150" style={{ transform: `scale(${zoom})` }}>
              <img src={selectedImage.url} alt={selectedImage.name} className="max-w-full max-h-[480px] rounded block" />

              {/* Bounding Boxes */}
              {(activeTab === 'detection' || activeTab === 'classification') &&
                result.detections.map((det) => (
                  <div
                    key={det.id}
                    style={{
                      left: `${det.x}%`,
                      top: `${det.y}%`,
                      width: `${det.width}%`,
                      height: `${det.height}%`,
                    }}
                    className={`absolute border-2 rounded-xs ${
                      det.severity === 'Critical'
                        ? 'border-red-500 bg-red-500/10'
                        : 'border-amber-400 bg-amber-400/10'
                    }`}
                  >
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 inline-block ${
                        det.severity === 'Critical' ? 'bg-red-600 text-white' : 'bg-amber-500 text-slate-950'
                      }`}
                    >
                      {det.label} ({Math.round(det.confidence * 100)}%)
                    </span>
                  </div>
                ))}

              {/* Segmentation Mask SVG Overlay */}
              {activeTab === 'segmentation' && (
                <svg
                  viewBox="0 0 1000 700"
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  preserveAspectRatio="none"
                >
                  {result.segmentations.map((seg) => (
                    <polygon
                      key={seg.id}
                      points={seg.points}
                      fill={seg.color}
                      fillOpacity={seg.opacity}
                      stroke={seg.color}
                      strokeWidth="3"
                    />
                  ))}
                </svg>
              )}

              {/* Explainability Heatmap Overlay */}
              {activeTab === 'explainability' && (
                <div
                  className="absolute inset-0 pointer-events-none rounded"
                  style={{
                    background:
                      'radial-gradient(circle at 38% 48%, rgba(239,68,68,0.55) 0%, rgba(245,158,11,0.35) 28%, rgba(8,145,178,0.12) 60%, transparent 80%)',
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: Results & Telemetry */}
        <div className="lg:col-span-3 bg-white rounded-lg border border-slate-200 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Analysis Summary</h2>
            <SeverityBadge severity={result.overallSeverity} />
          </div>

          <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 flex items-center gap-1">
                <Cpu className="w-3.5 h-3.5" /> Model
              </span>
              <span className="font-mono font-medium text-slate-800">{result.modelName}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Mean Confidence</span>
              <span className="font-mono font-semibold text-slate-900">{Math.round(result.confidenceMean * 100)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Inference Time</span>
              <span className="font-mono text-slate-700">{result.inferenceTimeMs} ms</span>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-900 mb-2">Detected Regions ({result.detections.length})</h3>
            <div className="space-y-2.5">
              {result.detections.map((det) => (
                <div key={det.id} className="p-2.5 rounded border border-slate-200 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-900">{det.label}</span>
                    <span className="font-mono text-[11px] text-cyan-700">{Math.round(det.confidence * 100)}%</span>
                  </div>
                  {det.estimatedLengthMm && (
                    <p className="text-[11px] text-slate-500 font-mono">
                      Est. {det.estimatedLengthMm}mm L × {det.estimatedWidthMm}mm W
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-900 mb-1.5">Engineering Recommendations</h3>
            <ul className="space-y-1.5 text-[11px] text-slate-600">
              {result.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-700 shrink-0 mt-0.5" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

