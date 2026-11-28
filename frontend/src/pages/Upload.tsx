import React, { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import {
  assetsApi,
  imagesApi,
  inspectionsApi,
  type InfrastructureAsset,
  type Inspection,
  type UploadResultItem,
} from '../api/client'

interface PreviewFile {
  id: string
  file: File
  previewUrl: string
  rotation: number
}

export const Upload: React.FC = () => {
  const { user, role } = useAuth()
  const navigate = useNavigate()

  // Selection states
  const [assets, setAssets] = useState<InfrastructureAsset[]>([])
  const [inspections, setInspections] = useState<Inspection[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState<number>(0)
  const [selectedInspectionId, setSelectedInspectionId] = useState<number>(0)
  const [source, setSource] = useState<string>('phone')

  // Files & Previews
  const [files, setFiles] = useState<PreviewFile[]>([])
  const [isDragging, setIsDragging] = useState(false)

  // Upload progress & feedback
  const [uploading, setUploading] = useState(false)
  const [creatingInspection, setCreatingInspection] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<UploadResultItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingInitial, setLoadingInitial] = useState(true)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  // Load available assets and authorized inspections
  useEffect(() => {
    const initData = async () => {
      try {
        setLoadingInitial(true)
        const [assetsData, inspectionsData] = await Promise.all([
          assetsApi.list({ page_size: 100 }),
          inspectionsApi.list(),
        ])

        setAssets(assetsData.items)

        // Eligible inspections (open or in-progress)
        const eligible = inspectionsData.filter((i) => {
          if (i.status === 'completed' || i.status === 'reviewed') return false
          return true
        })

        setInspections(eligible)
        if (eligible.length > 0) {
          setSelectedInspectionId(eligible[0].inspection_id)
          setSelectedAssetId(eligible[0].asset_id)
        } else if (assetsData.items.length > 0) {
          setSelectedAssetId(assetsData.items[0].asset_id)
          setSelectedInspectionId(0)
        }
      } catch (err: any) {
        setError(
          err.response?.data?.detail || 'Failed to load assets or inspections.',
        )
      } finally {
        setLoadingInitial(false)
      }
    }
    initData()
  }, [user, role])

  // Quick auto-create an inspection session if none exists
  const handleQuickCreateInspection = async (assetIdOverride?: number): Promise<number | null> => {
    const assetId = assetIdOverride || selectedAssetId || (assets[0]?.asset_id ?? 1)
    try {
      setCreatingInspection(true)
      setError(null)
      const newInsp = await inspectionsApi.create({
        asset_id: assetId,
        inspection_date: new Date().toISOString().split('T')[0],
        inspector_id: user?.user_id,
        status: 'in_progress',
        notes: `Field Inspection initialized via Direct Photo Ingestion for asset #${assetId}`,
      })
      setInspections((prev) => [newInsp, ...prev])
      setSelectedInspectionId(newInsp.inspection_id)
      setSelectedAssetId(assetId)
      return newInsp.inspection_id
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initialize inspection session.')
      return null
    } finally {
      setCreatingInspection(false)
    }
  }

  // Update selected inspection when asset selection changes
  const handleAssetChange = (assetId: number) => {
    setSelectedAssetId(assetId)
    const matching = inspections.filter((i) => i.asset_id === assetId)
    if (matching.length > 0) {
      setSelectedInspectionId(matching[0].inspection_id)
    } else {
      setSelectedInspectionId(0)
    }
  }

  // File addition helper
  const addFiles = (newFiles: FileList | File[]) => {
    setError(null)
    setResults(null)
    const previewList: PreviewFile[] = Array.from(newFiles).map((file) => ({
      id: Math.random().toString(36).substring(2, 9),
      file,
      previewUrl: URL.createObjectURL(file),
      rotation: 0,
    }))
    setFiles((prev) => [...prev, ...previewList])
  }

  // Remove single file
  const removeFile = (id: string) => {
    setFiles((prev) => {
      const target = prev.find((f) => f.id === id)
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((f) => f.id !== id)
    })
  }

  // Rotate preview by 90 degrees
  const rotateFile = (id: string) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === id ? { ...f, rotation: (f.rotation + 90) % 360 } : f,
      ),
    )
  }

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files)
    }
  }

  // Submit batch upload
  const handleUploadSubmit = async () => {
    if (files.length === 0) {
      setError('Please select or capture at least one image file.')
      return
    }

    let targetInspectionId = selectedInspectionId
    if (!targetInspectionId || targetInspectionId === 0) {
      // Auto-create inspection session on the fly
      const createdId = await handleQuickCreateInspection()
      if (!createdId) return
      targetInspectionId = createdId
    }

    try {
      setUploading(true)
      setProgress(0)
      setError(null)
      setResults(null)

      const rawFiles = files.map((f) => f.file)
      const resp = await imagesApi.upload(
        targetInspectionId,
        rawFiles,
        source,
        (pct) => setProgress(pct),
      )

      setResults(resp.results)
      // Clean up previews if all were accepted
      if (resp.rejected_count === 0) {
        files.forEach((f) => URL.revokeObjectURL(f.previewUrl))
        setFiles([])
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Upload failed. Please check network connection and credentials.',
      )
    } finally {
      setUploading(false)
    }
  }

  // Filtered inspections matching the selected asset
  const filteredInspections = selectedAssetId
    ? inspections.filter((i) => i.asset_id === selectedAssetId)
    : inspections

  return (
    <div className="min-h-screen bg-[#141619] text-white flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <div className="text-xs font-mono font-semibold text-[#0A21C0] uppercase tracking-wider mb-1">
            Data Ingestion & Quality Control
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Inspection Photo Upload
          </h1>
          <p className="text-xs sm:text-sm text-[#B3B4BD] mt-1">
            Capture or upload structural inspection photos with automated blur (Laplacian variance) and brightness validation.
          </p>
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs sm:text-sm rounded-xl flex justify-between items-center backdrop-blur-md">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white font-bold ml-4">&times;</button>
          </div>
        )}

        {loadingInitial ? (
          <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-12 text-center text-xs text-[#B3B4BD] animate-pulse">
            <div className="w-8 h-8 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            Loading active inspection schedules...
          </div>
        ) : (
          <div className="space-y-6">
            {/* Quick Inspection info banner if none active */}
            {inspections.length === 0 && (
              <div className="p-4 bg-blue-950/40 border border-blue-500/30 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-blue-200">
                <div className="flex items-center gap-2">
                  <span className="text-base">⚡</span>
                  <span><strong>Quick Inspection Mode:</strong> No active schedule currently assigned. Uploading photos will automatically initialize a field inspection record for this asset and analyze images immediately.</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleQuickCreateInspection()}
                  disabled={creatingInspection}
                  className="px-4 py-1.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white font-semibold rounded-full shadow shrink-0 cursor-pointer disabled:opacity-50"
                >
                  {creatingInspection ? 'Initializing...' : '+ Start Inspection'}
                </button>
              </div>
            )}

            {/* Target Selection Form */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#0A21C0] mb-4">
                Inspection Target & Metadata
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                {/* Asset Dropdown */}
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Infrastructure Asset
                  </label>
                  <select
                    value={selectedAssetId}
                    onChange={(e) => handleAssetChange(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
                  >
                    {assets.map((a) => (
                      <option key={a.asset_id} value={a.asset_id}>
                        {a.name} ({a.asset_type})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Inspection Dropdown */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="font-medium text-[#B3B4BD]">
                      Inspection Schedule
                    </label>
                    <button
                      type="button"
                      onClick={() => handleQuickCreateInspection()}
                      disabled={creatingInspection}
                      className="text-[10px] text-[#0A21C0] hover:underline font-semibold"
                    >
                      + New Session
                    </button>
                  </div>
                  <select
                    value={selectedInspectionId}
                    onChange={(e) =>
                      setSelectedInspectionId(Number(e.target.value))
                    }
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
                  >
                    {filteredInspections.length === 0 ? (
                      <option value="0">⚡ Auto-create inspection on upload</option>
                    ) : (
                      <>
                        <option value="0">⚡ Auto-create new session on upload</option>
                        {filteredInspections.map((i) => (
                          <option key={i.inspection_id} value={i.inspection_id}>
                            #{i.inspection_id} - {new Date(i.inspection_date).toLocaleDateString()} ({i.status})
                          </option>
                        ))}
                      </>
                    )}
                  </select>
                </div>

                {/* Source Dropdown */}
                <div>
                  <label className="block font-medium text-[#B3B4BD] mb-1">
                    Image Source Hardware
                  </label>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    className="w-full px-3 py-2 bg-[#141619] border border-[#2C2E3A] focus:border-[#0A21C0] rounded-xl text-xs text-white focus:outline-none"
                  >
                    <option value="phone">Field Smartphone Camera</option>
                    <option value="camera">Handheld DSLR / Industrial Camera</option>
                    <option value="drone">Autonomous Drone / UAV Platform</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Drag & Drop Upload Zone */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#0A21C0] mb-4">
                Upload or Capture Inspection Photos
              </h2>

              {/* Hidden file inputs */}
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/jpg"
                ref={fileInputRef}
                onChange={(e) => e.target.files && addFiles(e.target.files)}
                className="hidden"
              />
              <input
                type="file"
                accept="image/*"
                capture="environment"
                ref={cameraInputRef}
                onChange={(e) => e.target.files && addFiles(e.target.files)}
                className="hidden"
              />

              {/* Drop area */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all ${
                  isDragging
                    ? 'border-[#0A21C0] bg-[#050A44]/50 shadow-lg shadow-[#0A21C0]/20'
                    : 'border-[#2C2E3A] hover:border-[#0A21C0]/60 bg-[#141619]/60'
                }`}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-center text-4xl">
                    📸
                  </div>
                  <div className="text-sm text-white font-medium">
                    <span
                      className="font-bold text-[#0A21C0] hover:underline cursor-pointer"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      Browse local files
                    </span>{' '}
                    or drag and drop high-resolution inspection photos here
                  </div>
                  <p className="text-xs text-[#B3B4BD]">
                    JPEG or PNG up to 25 MB each &bull; Minimum 227 x 227 px resolution required
                  </p>

                  <div className="pt-2 flex justify-center space-x-3">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-5 py-2.5 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-white rounded-full text-xs font-semibold transition-all cursor-pointer"
                    >
                      Choose Images
                    </button>
                    <button
                      type="button"
                      onClick={() => cameraInputRef.current?.click()}
                      className="px-5 py-2.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full text-xs font-semibold shadow-md shadow-[#0A21C0]/30 transition-all flex items-center space-x-1 cursor-pointer"
                    >
                      <span>📷 Open Camera</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Preview Grid */}
              {files.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                      Selected Photos ({files.length})
                    </h3>
                    <button
                      onClick={() => {
                        files.forEach((f) => URL.revokeObjectURL(f.previewUrl))
                        setFiles([])
                      }}
                      className="text-xs text-rose-400 hover:text-rose-300 font-semibold cursor-pointer"
                    >
                      Clear All
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    {files.map((item) => (
                      <div
                        key={item.id}
                        className="bg-[#141619] rounded-xl border border-[#2C2E3A] p-2 relative group overflow-hidden"
                      >
                        <div className="h-32 w-full flex items-center justify-center overflow-hidden bg-[#050A44]/30 rounded-lg">
                          <img
                            src={item.previewUrl}
                            alt={item.file.name}
                            style={{
                              transform: `rotate(${item.rotation}deg)`,
                              transition: 'transform 0.2s',
                            }}
                            className="max-h-full max-w-full object-contain"
                          />
                        </div>

                        <div className="mt-2 text-[11px] truncate font-semibold text-white">
                          {item.file.name}
                        </div>
                        <div className="text-[10px] text-[#B3B4BD]">
                          {(item.file.size / (1024 * 1024)).toFixed(2)} MB
                        </div>

                        {/* Rotate & Remove controls */}
                        <div className="mt-2 flex items-center justify-between border-t border-[#2C2E3A] pt-1.5 text-xs">
                          <button
                            type="button"
                            onClick={() => rotateFile(item.id)}
                            title="Rotate preview"
                            className="text-[#B3B4BD] hover:text-white font-medium cursor-pointer"
                          >
                            ↻ Rotate
                          </button>
                          <button
                            type="button"
                            onClick={() => removeFile(item.id)}
                            title="Remove file"
                            className="text-rose-400 hover:text-rose-300 font-semibold cursor-pointer"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Progress bar */}
                  {uploading && (
                    <div className="mt-6 space-y-2">
                      <div className="flex justify-between text-xs font-semibold text-[#B3B4BD]">
                        <span>Uploading & analyzing image quality...</span>
                        <span className="text-[#0A21C0]">{progress}%</span>
                      </div>
                      <div className="w-full bg-[#141619] rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-[#0A21C0] h-2 transition-all duration-300 rounded-full"
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {/* Upload Action */}
                  <div className="mt-6">
                    <button
                      type="button"
                      onClick={handleUploadSubmit}
                      disabled={uploading || files.length === 0}
                      className="w-full py-3 bg-[#0A21C0] hover:bg-[#081ba0] text-white font-semibold rounded-full text-xs sm:text-sm shadow-lg shadow-[#0A21C0]/30 transition-all disabled:opacity-50 cursor-pointer"
                    >
                      {uploading
                        ? 'Validating Quality & Ingesting...'
                        : selectedInspectionId === 0
                        ? `⚡ Initialize Inspection & Ingest ${files.length} Photo${files.length > 1 ? 's' : ''}`
                        : `Upload & Ingest ${files.length} Photo${files.length > 1 ? 's' : ''}`}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Quality Results Table */}
            {results && (
              <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-[#141619]">
                  <div>
                    <h2 className="text-base font-bold text-white">
                      Ingestion & Quality Assessment Results
                    </h2>
                    <p className="text-xs text-[#B3B4BD]">
                      Automated OpenCV Laplacian sharpness and luminance validation completed.
                    </p>
                  </div>

                  {selectedInspectionId > 0 && (
                    <button
                      onClick={() => navigate(`/inspections/${selectedInspectionId}`)}
                      className="px-5 py-2.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white font-semibold rounded-full text-xs shadow-md shadow-[#0A21C0]/30 transition-all cursor-pointer"
                    >
                      ⚡ Open Inspection & Run AI Assessment &rarr;
                    </button>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-[#141619] text-xs text-left">
                    <thead className="bg-[#141619]/80 text-[#B3B4BD] font-mono text-[10px] uppercase tracking-wider">
                      <tr>
                        <th className="px-4 py-3">File Name</th>
                        <th className="px-4 py-3">Result</th>
                        <th className="px-4 py-3">Quality Details</th>
                        <th className="px-4 py-3">Sharpness / Brightness</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#141619]/60 text-white">
                      {results.map((res, idx) => (
                        <tr key={idx} className="hover:bg-[#141619]/40">
                          <td className="px-4 py-3 font-mono font-medium text-white">
                            {res.filename}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                res.status === 'accepted'
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : res.status === 'warning'
                                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              }`}
                            >
                              {res.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-[#B3B4BD]">
                            {res.message}
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-[#B3B4BD]">
                            {res.image ? (
                              <span>
                                Sharpness: <strong className="text-white">{res.image.blur_score.toFixed(1)}</strong> &bull; Luminance: <strong className="text-white">{res.image.brightness_score.toFixed(1)}</strong>
                              </span>
                            ) : (
                              '-'
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {results.some((r) => r.status === 'rejected') && (
                  <div className="mt-4 p-3 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs rounded-xl">
                    <strong>Note:</strong> Photos rejected due to severe motion blur or low resolution were not committed to storage.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default Upload
