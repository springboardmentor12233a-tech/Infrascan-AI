import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ZoomIn, ZoomOut, RotateCw, Download, ScanSearch, AlertCircle } from 'lucide-react'
import { imageService } from '@/services/imageService'
import { AIProcessingBadge } from '@/components/inspections/AIProcessingBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'
import { formatBytes, formatDateTime } from '@/lib/utils'

export function ImageDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)

  const { data: image, isLoading } = useQuery({
    queryKey: ['image', id],
    queryFn: () => imageService.getById(id!),
    enabled: Boolean(id),
  })

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading image workspace...</div>
  }

  if (!image) {
    return (
      <div className="p-8 text-center space-y-2">
        <p className="text-sm font-semibold text-slate-900">Image Not Found</p>
        <Link to="/app/images" className="text-xs text-cyan-700 hover:underline">
          Back to Image Repository
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link to="/app/images" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Image Repository
          </Link>
          <h1 className="text-xl font-semibold text-slate-900 font-mono">{image.filename}</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {image.assetName} · Inspection {image.inspectionId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={image.url}
            download={image.filename}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium"
          >
            <Download className="w-3.5 h-3.5" /> Download
          </a>
          <Link
            to="/app/analysis"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
          >
            <ScanSearch className="w-3.5 h-3.5" /> Analyze in AI Workspace
          </Link>
        </div>
      </div>

      <DemoBanner message="Demonstration Metadata: Image quality assessment and calibration values are simulated for frontend evaluation prior to OpenCV/FastAPI backend integration." />

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Viewer */}
        <div className="lg:col-span-8 bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700">Image Viewer</span>
            <div className="flex items-center gap-1">
              <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} className="p-1.5 rounded hover:bg-slate-200"><ZoomOut className="w-3.5 h-3.5" /></button>
              <span className="text-[11px] font-mono w-10 text-center">{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom((z) => Math.min(2.5, z + 0.25))} className="p-1.5 rounded hover:bg-slate-200"><ZoomIn className="w-3.5 h-3.5" /></button>
              <button onClick={() => setRotation((r) => (r + 90) % 360)} className="p-1.5 rounded hover:bg-slate-200"><RotateCw className="w-3.5 h-3.5" /></button>
            </div>
          </div>
          <div className="bg-slate-950 min-h-[420px] flex items-center justify-center overflow-auto p-4">
            <img
              src={image.url}
              alt={image.filename}
              style={{ transform: `scale(${zoom}) rotate(${rotation}deg)` }}
              className="max-w-full max-h-[460px] transition-transform duration-150 rounded"
            />
          </div>
        </div>

        {/* Metadata, Quality & Calibration */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2.5 text-xs">
            <h2 className="font-semibold text-slate-900 border-b border-slate-100 pb-2">Image Information</h2>
            <div className="flex justify-between"><span className="text-slate-500">Image ID</span><span className="font-mono font-medium">{image.id}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Resolution</span><span>{image.resolution}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">File Size</span><span>{formatBytes(image.fileSizeBytes)}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Camera</span><span>{image.cameraModel}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Uploaded</span><span>{formatDateTime(image.uploadDate)}</span></div>
            <div className="flex justify-between items-center"><span className="text-slate-500">AI Status</span><AIProcessingBadge status={image.processingStatus} /></div>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2.5 text-xs">
            <h2 className="font-semibold text-slate-900 border-b border-slate-100 pb-2">Quality Assessment (Simulated)</h2>
            <div className="flex justify-between"><span className="text-slate-500">Overall Status</span><span className="font-semibold text-emerald-700">{image.qualityStatus || 'Good Quality'}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Sharpness / Blur</span><span>Pass (Simulated)</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Brightness / Contrast</span><span>Optimal (Simulated)</span></div>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2.5 text-xs">
            <h2 className="font-semibold text-slate-900 border-b border-slate-100 pb-2">Calibration Metadata</h2>
            <div className="flex justify-between"><span className="text-slate-500">Status</span><span className="font-medium">{image.calibrationStatus || (image.calibrated ? 'Calibration Verified' : 'Not Calibrated')}</span></div>
            {image.calibrated && image.pxPerMm ? (
              <div className="flex justify-between"><span className="text-slate-500">Scale</span><span className="font-mono">{image.pxPerMm} px/mm</span></div>
            ) : (
              <p className="text-[11px] text-amber-700 bg-amber-50 p-2 rounded border border-amber-200 flex items-start gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                Physical millimeter measurements are unavailable without reference calibration.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

