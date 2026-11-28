import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, UploadCloud, Trash2, CheckCircle2 } from 'lucide-react'
import { MOCK_ASSETS, MOCK_INSPECTIONS } from '@/data/mockData'
import { imageService } from '@/services/imageService'
import { formatBytes } from '@/lib/utils'

interface QueuedFile {
  name: string
  size: number
  type: string
  url: string
}

export function ImageUploadPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [assetId, setAssetId] = useState(MOCK_ASSETS[0].id)
  const matchingInspections = MOCK_INSPECTIONS.filter((i) => i.assetId === assetId)
  const [inspectionId, setInspectionId] = useState(matchingInspections[0]?.id || MOCK_INSPECTIONS[0].id)
  const [category, setCategory] = useState('Crack Evidence')
  const [captureMethod, setCaptureMethod] = useState('UAV')
  const [description, setDescription] = useState('')
  const [calibrated, setCalibrated] = useState(false)
  const [pxPerMm, setPxPerMm] = useState('2.0')
  const [files, setFiles] = useState<QueuedFile[]>([])

  const selectedAsset = MOCK_ASSETS.find((a) => a.id === assetId) || MOCK_ASSETS[0]

  const uploadMutation = useMutation({
    mutationFn: () =>
      imageService.uploadBulk(
        files.map((f) => ({
          filename: f.name,
          url: f.url,
          assetId: selectedAsset.id,
          assetName: selectedAsset.name,
          inspectionId,
          uploadDate: new Date().toISOString(),
          resolution: '4000 x 3000',
          fileSizeBytes: f.size,
          cameraModel: captureMethod,
          calibrated,
          pxPerMm: calibrated ? Number(pxPerMm) : undefined,
          hasAiAnalysis: false,
          processingStatus: 'Not Started',
          qualityStatus: 'Good Quality',
          calibrationStatus: calibrated ? 'Calibration Available' : 'Not Calibrated',
          category,
          captureMethod,
          description,
        }))
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] })
      navigate('/app/images')
    },
  })

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return
    const valid = Array.from(fileList)
      .filter((f) => ['image/jpeg', 'image/png', 'image/webp'].includes(f.type) && f.size <= 25 * 1024 * 1024)
      .map((f) => ({ name: f.name, size: f.size, type: f.type, url: URL.createObjectURL(f) }))
    setFiles((prev) => [...prev, ...valid])
  }

  return (
    <div className="space-y-5 max-w-5xl">
      <div>
        <Link to="/app/images" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Image Repository
        </Link>
        <h1 className="text-xl font-semibold text-slate-900">Upload Inspection Images</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Acquire structural photographs, associate with assets & inspections, and prepare for AI analysis
        </p>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-5">
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              handleFiles(e.dataTransfer.files)
            }}
            className="bg-white border-2 border-dashed border-slate-300 hover:border-cyan-600 rounded-lg p-10 text-center cursor-pointer transition-colors"
          >
            <UploadCloud className="w-9 h-9 text-cyan-700 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-900">Drag & drop inspection images here</p>
            <p className="text-xs text-slate-500 mt-1">Supported: JPG, JPEG, PNG, WEBP · Max 25 MB per file</p>
            <input ref={fileRef} type="file" multiple accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
          </div>

          {files.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
              <p className="text-xs font-semibold text-slate-900">Selected Files ({files.length})</p>
              <div className="space-y-2">
                {files.map((f, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded border border-slate-200 text-xs">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <img src={f.url} alt={f.name} className="w-10 h-10 object-cover rounded" />
                      <div className="min-w-0">
                        <p className="font-mono font-medium text-slate-900 truncate">{f.name}</p>
                        <p className="text-[11px] text-slate-500">{formatBytes(f.size)}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setFiles((prev) => prev.filter((_, i) => i !== idx))}
                      className="p-1 text-slate-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-5 bg-white rounded-lg border border-slate-200 p-5 space-y-4 text-xs">
          <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
            Association & Metadata
          </h2>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Infrastructure Asset *</label>
            <select
              value={assetId}
              onChange={(e) => {
                setAssetId(e.target.value)
                const first = MOCK_INSPECTIONS.find((i) => i.assetId === e.target.value)
                if (first) setInspectionId(first.id)
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white"
            >
              {MOCK_ASSETS.map((a) => (
                <option key={a.id} value={a.id}>{a.id} — {a.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Associated Inspection *</label>
            <select
              value={inspectionId}
              onChange={(e) => setInspectionId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white"
            >
              {(matchingInspections.length > 0 ? matchingInspections : MOCK_INSPECTIONS).map((i) => (
                <option key={i.id} value={i.id}>{i.id} ({i.date})</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Image Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full px-2.5 py-2 border border-slate-300 rounded-md bg-white">
                <option>General Inspection</option>
                <option>Crack Evidence</option>
                <option>Surface Damage</option>
                <option>Structural Defect</option>
                <option>Reference Image</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Capture Method</label>
              <select value={captureMethod} onChange={(e) => setCaptureMethod(e.target.value)} className="w-full px-2.5 py-2 border border-slate-300 rounded-md bg-white">
                <option>UAV</option>
                <option>DSLR Camera</option>
                <option>Mobile Camera</option>
                <option>Drone</option>
                <option>Other</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Description</label>
            <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div className="pt-2 border-t border-slate-100 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer font-medium text-slate-700">
              <input type="checkbox" checked={calibrated} onChange={(e) => setCalibrated(e.target.checked)} />
              Reference Calibration Available
            </label>
            {calibrated && (
              <input
                type="number"
                step="0.1"
                value={pxPerMm}
                onChange={(e) => setPxPerMm(e.target.value)}
                placeholder="Pixels per mm"
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              />
            )}
          </div>
          <div className="pt-3 flex justify-end gap-2">
            <button type="button" onClick={() => navigate('/app/images')} className="px-4 py-2 border border-slate-200 rounded-md">
              Cancel
            </button>
            <button
              type="button"
              disabled={files.length === 0 || uploadMutation.isPending}
              onClick={() => uploadMutation.mutate()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F2942] text-white rounded-md font-semibold disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {uploadMutation.isPending ? 'Uploading...' : `Upload ${files.length} Image(s)`}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

