import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { AuthenticatedImage } from '../components/AuthenticatedImage'
import { useAuth } from '../context/AuthContext'
import {
  imagesApi,
  inspectionsApi,
  type ImageMetadata,
  type Inspection,
} from '../api/client'

export const InspectionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user, role } = useAuth()

  const [inspection, setInspection] = useState<Inspection | null>(null)
  const [images, setImages] = useState<ImageMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Track per-image view mode: 'original' vs 'processed'
  const [activeTabMap, setActiveTabMap] = useState<Record<number, 'original' | 'processed'>>({})
  // Track preprocessing in progress
  const [reprocessingId, setReprocessingId] = useState<number | null>(null)
  const [reprocessingAll, setReprocessingAll] = useState(false)

  const inspectionId = id ? parseInt(id, 10) : 0

  const fetchData = async () => {
    if (!inspectionId) return
    try {
      setLoading(true)
      setError(null)
      const [inspData, imgsData] = await Promise.all([
        inspectionsApi.getById(inspectionId),
        imagesApi.listByInspection(inspectionId),
      ])
      setInspection(inspData)
      setImages(imgsData)
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Failed to load inspection or photos.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [inspectionId])

  // Delete an image
  const handleDeleteImage = async (imageId: number) => {
    if (!window.confirm(`Are you sure you want to delete image #${imageId}?`)) {
      return
    }
    try {
      setError(null)
      setActionSuccess(null)
      await imagesApi.delete(imageId)
      setActionSuccess(`Image #${imageId} deleted successfully.`)
      fetchData()
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Failed to delete image. Completed inspections cannot have photos removed.',
      )
    }
  }

  // Re-run preprocessing for a single image
  const handlePreprocessSingle = async (imageId: number) => {
    try {
      setReprocessingId(imageId)
      setError(null)
      setActionSuccess(null)
      const updated = await imagesApi.preprocessImage(imageId)
      setImages((prev) =>
        prev.map((img) => (img.image_id === imageId ? updated : img)),
      )
      // Switch view to processed
      setActiveTabMap((prev) => ({ ...prev, [imageId]: 'processed' }))
      setActionSuccess(`Image #${imageId} preprocessed successfully.`)
    } catch (err: any) {
      setError(
        err.response?.data?.detail || `Failed to preprocess image #${imageId}.`,
      )
    } finally {
      setReprocessingId(null)
    }
  }

  // Re-run preprocessing for all images in this inspection
  const handlePreprocessAll = async () => {
    if (!inspectionId) return
    try {
      setReprocessingAll(true)
      setError(null)
      setActionSuccess(null)
      const updatedList = await imagesApi.preprocessInspection(inspectionId)
      setImages(updatedList)
      // Switch all to processed view
      const newTabs: Record<number, 'original' | 'processed'> = {}
      updatedList.forEach((img) => {
        newTabs[img.image_id] = 'processed'
      })
      setActiveTabMap(newTabs)
      setActionSuccess(
        `Preprocessing completed for all ${updatedList.length} photos.`,
      )
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Failed to run inspection batch preprocessing.',
      )
    } finally {
      setReprocessingAll(false)
    }
  }

  const canUpload =
    role === 'admin' ||
    role === 'civil_engineer' ||
    (role === 'inspector' && inspection?.inspector_id === user?.user_id)

  const canReprocessAll = role === 'admin' || role === 'civil_engineer'

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-center justify-between">
          <Link
            to="/inspections"
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>&larr;</span>
            <span>Back to Inspections Registry</span>
          </Link>
          <div className="flex items-center space-x-3">
            {canReprocessAll && images.length > 0 && (
              <button
                onClick={handlePreprocessAll}
                disabled={reprocessingAll}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1"
              >
                <span>{reprocessingAll ? 'Processing All...' : '⚡ Re-run Pipeline (All Photos)'}</span>
              </button>
            )}
            {canUpload && (
              <Link
                to="/upload"
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
              >
                + Upload Photos
              </Link>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg flex justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-500 font-bold">&times;</button>
          </div>
        )}

        {actionSuccess && (
          <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg flex justify-between">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="text-emerald-500 font-bold">&times;</button>
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center text-sm text-slate-500 animate-pulse">
            Loading inspection and images...
          </div>
        ) : !inspection ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center text-sm text-slate-500">
            Inspection not found.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header info */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-semibold text-slate-400">
                      INSPECTION #{inspection.inspection_id}
                    </span>
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold uppercase ${
                        inspection.status === 'completed'
                          ? 'bg-emerald-50 text-emerald-700'
                          : inspection.status === 'in_progress'
                          ? 'bg-amber-50 text-amber-700'
                          : inspection.status === 'reviewed'
                          ? 'bg-purple-50 text-purple-700'
                          : 'bg-blue-50 text-blue-700'
                      }`}
                    >
                      {inspection.status.replace('_', ' ')}
                    </span>
                  </div>
                  <h1 className="text-xl font-bold text-slate-900 mt-1">
                    {inspection.asset_name || `Asset #${inspection.asset_id}`}
                  </h1>
                </div>

                <div className="text-xs text-slate-600 sm:text-right">
                  <div>
                    <span className="text-slate-400">Scheduled Date: </span>
                    <span className="text-slate-700 font-medium">
                      {new Date(inspection.inspection_date).toLocaleDateString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Assigned Inspector: </span>
                    <span className="font-semibold text-slate-800">
                      {inspection.inspector_name || `User #${inspection.inspector_id}`}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Total Photos: </span>
                    <span className="font-semibold text-slate-800">
                      {images.length}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Image Gallery */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Inspection Photo Gallery
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Compare original photographs with CLAHE-enhanced model inputs.
                  </p>
                </div>
              </div>

              {images.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded-lg border border-dashed border-slate-200">
                  <p className="mb-3">No photos uploaded for this inspection yet.</p>
                  {canUpload && (
                    <Link
                      to="/upload"
                      className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold inline-block"
                    >
                      Upload First Photo
                    </Link>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {images.map((img) => {
                    const currentTab =
                      activeTabMap[img.image_id] ||
                      (img.preprocess_status === 'done' ? 'processed' : 'original')

                    const isReprocessingThis = reprocessingId === img.image_id
                    const canUserReprocess =
                      role === 'admin' ||
                      role === 'civil_engineer' ||
                      img.uploaded_by === user?.user_id

                    return (
                      <div
                        key={img.image_id}
                        className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm flex flex-col transition hover:shadow-md"
                      >
                        {/* Toggle header between Original and Processed */}
                        <div className="bg-slate-100 p-1.5 flex items-center justify-between border-b border-slate-200 text-xs">
                          <div className="flex space-x-1">
                            <button
                              onClick={() =>
                                setActiveTabMap((prev) => ({
                                  ...prev,
                                  [img.image_id]: 'original',
                                }))
                              }
                              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                                currentTab === 'original'
                                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                                  : 'text-slate-500 hover:text-slate-800'
                              }`}
                            >
                              Original
                            </button>
                            <button
                              onClick={() =>
                                setActiveTabMap((prev) => ({
                                  ...prev,
                                  [img.image_id]: 'processed',
                                }))
                              }
                              className={`px-3 py-1 rounded text-xs font-medium transition-colors flex items-center space-x-1 ${
                                currentTab === 'processed'
                                  ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                                  : 'text-slate-500 hover:text-slate-800'
                              }`}
                            >
                              <span>Enhanced</span>
                              {img.preprocess_status === 'done' && (
                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                              )}
                            </button>
                          </div>

                          {/* Preprocess Status Badge */}
                          <div>
                            {img.preprocess_status === 'not_run' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 animate-pulse">
                                Processing...
                              </span>
                            )}
                            {img.preprocess_status === 'failed' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-700">
                                Preprocess Failed
                              </span>
                            )}
                            {img.preprocess_status === 'done' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                                Preprocessed
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Image Viewer Container */}
                        <div className="h-56 w-full bg-slate-900 flex items-center justify-center overflow-hidden relative">
                          {currentTab === 'original' ? (
                            <AuthenticatedImage
                              imageId={img.image_id}
                              alt={img.original_filename}
                              isProcessed={false}
                              className="max-h-full max-w-full object-contain"
                            />
                          ) : img.preprocess_status === 'done' ? (
                            <AuthenticatedImage
                              imageId={img.image_id}
                              alt={`Enhanced ${img.original_filename}`}
                              isProcessed={true}
                              className="max-h-full max-w-full object-contain"
                            />
                          ) : img.preprocess_status === 'failed' ? (
                            <div className="text-center p-4 text-rose-300 text-xs">
                              <p className="font-semibold mb-1">Preprocessing failed</p>
                              <p className="text-[10px] text-rose-400">
                                {img.preprocess_steps || 'Could not enhance image'}
                              </p>
                            </div>
                          ) : (
                            <div className="text-center p-4 text-slate-400 text-xs animate-pulse">
                              <p className="font-semibold mb-1">Preprocessing pipeline in progress...</p>
                              <p className="text-[10px] text-slate-500">
                                Generating CLAHE enhanced input
                              </p>
                            </div>
                          )}

                          {/* Quality status badge overlaid */}
                          <div className="absolute top-2 right-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase shadow-sm ${
                                img.quality_status === 'passed'
                                  ? 'bg-emerald-600 text-white'
                                  : img.quality_status === 'warning'
                                  ? 'bg-amber-500 text-white'
                                  : 'bg-rose-600 text-white'
                              }`}
                            >
                              {img.quality_status}
                            </span>
                          </div>

                          {/* Active view indicator */}
                          <div className="absolute bottom-2 left-2 bg-slate-900/80 px-2 py-0.5 rounded text-[10px] font-medium text-slate-200 backdrop-blur-xs">
                            {currentTab === 'original' ? 'Original (Full-Res)' : 'Enhanced (CLAHE / LAB)'}
                          </div>
                        </div>

                        {/* Card Content & Metadata */}
                        <div className="p-4 flex-1 flex flex-col justify-between text-xs">
                          <div>
                            <div
                              className="font-semibold text-slate-800 truncate"
                              title={img.original_filename}
                            >
                              {img.original_filename}
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5">
                              {img.width_px} x {img.height_px} px &bull;{' '}
                              {(img.file_size_bytes / (1024 * 1024)).toFixed(2)} MB &bull; Source: {img.source}
                            </div>

                            {/* Quality Metrics */}
                            <div className="mt-3 p-2 bg-slate-50 rounded-lg border border-slate-100 text-[11px] space-y-1">
                              <div className="flex justify-between">
                                <span className="text-slate-500">Sharpness / Blur:</span>
                                <span className="font-mono font-medium text-slate-700">
                                  {img.blur_score.toFixed(1)}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Brightness:</span>
                                <span className="font-mono font-medium text-slate-700">
                                  {img.brightness_score.toFixed(1)}
                                </span>
                              </div>
                              {img.quality_notes && (
                                <div className="pt-1 text-slate-600 border-t border-slate-200 text-[10px]">
                                  {img.quality_notes}
                                </div>
                              )}
                            </div>

                            {/* Steps applied */}
                            {img.preprocess_steps && (
                              <div className="mt-3">
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                                  Steps Applied:
                                </span>
                                <div className="flex flex-wrap gap-1">
                                  {img.preprocess_steps.split(',').map((step, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-0.5 rounded text-[10px] bg-indigo-50 text-indigo-700 font-mono font-medium"
                                    >
                                      {step.trim()}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* GPS coordinates */}
                            {(img.gps_latitude || img.gps_longitude) && (
                              <div className="mt-2 text-[10px] text-slate-500">
                                📍 GPS: {img.gps_latitude?.toFixed(4)}, {img.gps_longitude?.toFixed(4)}
                              </div>
                            )}
                          </div>

                          {/* Footer with action buttons */}
                          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                            {canUserReprocess && (
                              <button
                                onClick={() => handlePreprocessSingle(img.image_id)}
                                disabled={isReprocessingThis}
                                className="text-indigo-600 hover:text-indigo-800 font-semibold disabled:opacity-50"
                              >
                                {isReprocessingThis ? 'Processing...' : '🔄 Re-run Preprocessing'}
                              </button>
                            )}

                            {(role === 'admin' ||
                              role === 'civil_engineer' ||
                              img.uploaded_by === user?.user_id) &&
                              inspection.status !== 'completed' && (
                                <button
                                  onClick={() => handleDeleteImage(img.image_id)}
                                  className="text-rose-600 hover:text-rose-800 font-semibold ml-auto"
                                >
                                  Delete
                                </button>
                              )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default InspectionDetailPage
