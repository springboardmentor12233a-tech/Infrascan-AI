import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
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

        // Filter inspections user is allowed to upload to:
        // Inspectors can only upload to their own non-completed inspections
        const eligible = inspectionsData.filter((i) => {
          if (i.status === 'completed' || i.status === 'reviewed') return false
          if (role === 'inspector') {
            return i.inspector_id === user?.user_id
          }
          return true
        })

        setInspections(eligible)
        if (eligible.length > 0) {
          setSelectedInspectionId(eligible[0].inspection_id)
          setSelectedAssetId(eligible[0].asset_id)
        } else if (assetsData.items.length > 0) {
          setSelectedAssetId(assetsData.items[0].asset_id)
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
    if (!selectedInspectionId) {
      setError('Please select an active inspection to upload images for.')
      return
    }
    if (files.length === 0) {
      setError('Please select or capture at least one image file.')
      return
    }

    try {
      setUploading(true)
      setProgress(0)
      setError(null)
      setResults(null)

      const rawFiles = files.map((f) => f.file)
      const resp = await imagesApi.upload(
        selectedInspectionId,
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
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Inspection Photo Upload
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Capture or upload structural inspection photos with automatic blur
            and brightness quality validation.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-500 font-bold">&times;</button>
          </div>
        )}

        {loadingInitial ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center text-sm text-slate-500 animate-pulse">
            Loading inspection scheduling details...
          </div>
        ) : inspections.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center text-sm text-slate-600">
            <p className="font-semibold text-slate-800 mb-2">No Active Inspections Found</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
              You do not have any active or in-progress inspections assigned to
              upload photos for.
            </p>
            <Link
              to="/inspections"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
            >
              Go to Inspections Registry &rarr;
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Target Selection Form */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">
                Inspection Target
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                {/* Asset Dropdown */}
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Infrastructure Asset
                  </label>
                  <select
                    value={selectedAssetId}
                    onChange={(e) => handleAssetChange(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                  <label className="block font-medium text-slate-700 mb-1">
                    Inspection Schedule
                  </label>
                  <select
                    value={selectedInspectionId}
                    onChange={(e) =>
                      setSelectedInspectionId(Number(e.target.value))
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    {filteredInspections.length === 0 ? (
                      <option value="0">No active inspection for asset</option>
                    ) : (
                      filteredInspections.map((i) => (
                        <option key={i.inspection_id} value={i.inspection_id}>
                          #{i.inspection_id} - {new Date(i.inspection_date).toLocaleDateString()} ({i.status})
                        </option>
                      ))
                    )}
                  </select>
                </div>

                {/* Source Dropdown */}
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Image Source
                  </label>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="phone">Phone Camera</option>
                    <option value="camera">Handheld Digital Camera</option>
                    <option value="drone">Drone / Aerial UAV</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Drag & Drop Upload Zone */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">
                Select or Capture Photos
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
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-50/50'
                    : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-center space-x-2 text-slate-400">
                    <span className="text-4xl">📸</span>
                  </div>
                  <div className="text-sm text-slate-600">
                    <span className="font-semibold text-indigo-600 cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                      Click to choose files
                    </span>{' '}
                    or drag and drop inspection images here
                  </div>
                  <p className="text-xs text-slate-400">
                    JPG, JPEG, PNG up to 20 MB each (min 640 x 480 resolution)
                  </p>

                  <div className="pt-2 flex justify-center space-x-3">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                    >
                      Choose Files
                    </button>
                    <button
                      type="button"
                      onClick={() => cameraInputRef.current?.click()}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1"
                    >
                      <span>📷 Camera</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Preview Grid */}
              {files.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Pending Upload ({files.length} photo{files.length > 1 ? 's' : ''})
                    </h3>
                    <button
                      onClick={() => {
                        files.forEach((f) => URL.revokeObjectURL(f.previewUrl))
                        setFiles([])
                      }}
                      className="text-xs text-rose-600 hover:text-rose-800"
                    >
                      Clear All
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    {files.map((item) => (
                      <div
                        key={item.id}
                        className="bg-slate-50 rounded-lg border border-slate-200 p-2 relative group overflow-hidden"
                      >
                        <div className="h-32 w-full flex items-center justify-center overflow-hidden bg-slate-900 rounded">
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

                        <div className="mt-2 text-[11px] truncate font-medium text-slate-700">
                          {item.file.name}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {(item.file.size / (1024 * 1024)).toFixed(2)} MB
                        </div>

                        {/* Rotate & Remove controls */}
                        <div className="mt-2 flex items-center justify-between border-t border-slate-200 pt-1.5 text-xs">
                          <button
                            type="button"
                            onClick={() => rotateFile(item.id)}
                            title="Rotate preview"
                            className="text-slate-600 hover:text-indigo-600 font-semibold"
                          >
                            ↻ Rotate
                          </button>
                          <button
                            type="button"
                            onClick={() => removeFile(item.id)}
                            title="Remove file"
                            className="text-rose-600 hover:text-rose-800 font-semibold"
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
                      <div className="flex justify-between text-xs font-semibold text-slate-600">
                        <span>Uploading inspection batch...</span>
                        <span>{progress}%</span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-2 transition-all duration-300 rounded-full"
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
                      disabled={uploading || !selectedInspectionId}
                      className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm shadow transition-colors disabled:opacity-50"
                    >
                      {uploading
                        ? 'Analyzing & Uploading...'
                        : `Upload ${files.length} Photo${files.length > 1 ? 's' : ''}`}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Results Table (Screen 4: accepted, warning, rejected per file) */}
            {results && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-bold text-slate-800">
                    Upload & Quality Analysis Results
                  </h2>
                  <Link
                    to={`/assets/${selectedAssetId}`}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    View Asset & Inspections &rarr;
                  </Link>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                    <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
                      <tr>
                        <th className="px-4 py-3">File Name</th>
                        <th className="px-4 py-3">Result</th>
                        <th className="px-4 py-3">Quality Details / Reason</th>
                        <th className="px-4 py-3">Scores</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {results.map((res, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/60">
                          <td className="px-4 py-3 font-mono text-slate-900 font-medium">
                            {res.filename}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2.5 py-0.5 rounded text-[11px] font-semibold uppercase ${
                                res.status === 'accepted'
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : res.status === 'warning'
                                  ? 'bg-amber-50 text-amber-700'
                                  : 'bg-rose-50 text-rose-700'
                              }`}
                            >
                              {res.status}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={
                                res.status === 'rejected'
                                  ? 'text-rose-600 font-medium'
                                  : res.status === 'warning'
                                  ? 'text-amber-800'
                                  : 'text-slate-600'
                              }
                            >
                              {res.message}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-slate-500">
                            {res.image ? (
                              <span>
                                Blur: {res.image.blur_score.toFixed(1)} | Bright: {res.image.brightness_score.toFixed(1)}
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
                  <div className="mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                    <strong>Note:</strong> Rejected photos were not saved. Please
                    adjust angle/resolution and retake the photo.
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
