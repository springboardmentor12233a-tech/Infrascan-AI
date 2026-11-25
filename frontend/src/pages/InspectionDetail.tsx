import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { AuthenticatedImage } from '../components/AuthenticatedImage'
import { AnalysisModal, getSeverityBadgeClass } from '../components/AnalysisModal'
import { useAuth } from '../context/AuthContext'
import {
  imagesApi,
  inspectionsApi,
  analysisApi,
  severityApi,
  assetsApi,
  type ImageMetadata,
  type Inspection,
  type InfrastructureAsset,
  type AnalysisRun,
  type SeverityAssessment,
  type InspectionSeverityDetail,
} from '../api/client'

export const InspectionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user, role } = useAuth()

  const [inspection, setInspection] = useState<Inspection | null>(null)
  const [asset, setAsset] = useState<InfrastructureAsset | null>(null)
  const [images, setImages] = useState<ImageMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Track per-image view mode: 'original' vs 'processed'
  const [activeTabMap, setActiveTabMap] = useState<Record<number, 'original' | 'processed'>>({})
  // Track preprocessing in progress
  const [reprocessingId, setReprocessingId] = useState<number | null>(null)
  const [reprocessingAll, setReprocessingAll] = useState(false)

  // AI Analysis states
  const [analysisMap, setAnalysisMap] = useState<Record<number, AnalysisRun | null>>({})
  const [analyzingImageId, setAnalyzingImageId] = useState<number | null>(null)
  const [analyzingAll, setAnalyzingAll] = useState(false)
  const [selectedForModal, setSelectedForModal] = useState<{
    image: ImageMetadata
    analysis: AnalysisRun
  } | null>(null)

  // Severity states
  const [inspectionSeverity, setInspectionSeverity] = useState<InspectionSeverityDetail | null>(null)
  const [severityMap, setSeverityMap] = useState<Record<number, SeverityAssessment | null>>({})

  const inspectionId = id ? parseInt(id, 10) : 0

  // Fetch AI analysis records for given list of images
  const fetchAnalysisForImages = async (imgs: ImageMetadata[]) => {
    const runs: Record<number, AnalysisRun | null> = {}
    await Promise.all(
      imgs.map(async (img) => {
        try {
          const run = await analysisApi.getImageAnalysis(img.image_id)
          runs[img.image_id] = run
        } catch {
          runs[img.image_id] = null
        }
      })
    )
    setAnalysisMap((prev) => ({ ...prev, ...runs }))
  }

  const fetchData = async () => {
    if (!inspectionId) return
    try {
      setLoading(true)
      setError(null)
      const [inspData, imgsData, sevData] = await Promise.all([
        inspectionsApi.getById(inspectionId),
        imagesApi.listByInspection(inspectionId),
        severityApi.getInspectionSeverity(inspectionId).catch(() => null),
      ])
      setInspection(inspData)
      if (inspData && inspData.asset_id) {
        assetsApi.getById(inspData.asset_id).then(setAsset).catch(() => setAsset(null))
      }
      setImages(imgsData)
      setInspectionSeverity(sevData)
      if (sevData && sevData.assessments) {
        const sMap: Record<number, SeverityAssessment> = {}
        sevData.assessments.forEach((a) => {
          sMap[a.image_id] = a
        })
        setSeverityMap(sMap)
      }
      fetchAnalysisForImages(imgsData)
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

  // Periodic polling if any analysis is pending or in_progress
  useEffect(() => {
    const hasPending = Object.values(analysisMap).some(
      (run) => run && (run.status === 'pending' || run.status === 'in_progress'),
    )
    if (!hasPending || images.length === 0) return

    const interval = setInterval(() => {
      fetchAnalysisForImages(images)
    }, 3000)

    return () => clearInterval(interval)
  }, [analysisMap, images])

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

  // Single-image AI analysis
  const handleAnalyzeSingle = async (imageId: number) => {
    try {
      setAnalyzingImageId(imageId)
      setError(null)
      setActionSuccess(null)
      const run = await analysisApi.analyzeImage(imageId)
      setAnalysisMap((prev) => ({ ...prev, [imageId]: run }))
      setActionSuccess(`AI analysis started for image #${imageId}.`)
    } catch (err: any) {
      setError(
        err.response?.data?.detail || `Failed to analyze image #${imageId}.`,
      )
    } finally {
      setAnalyzingImageId(null)
    }
  }

  // Batch AI analysis for the whole inspection
  const handleAnalyzeAll = async () => {
    if (!inspectionId) return
    try {
      setAnalyzingAll(true)
      setError(null)
      setActionSuccess(null)
      const batchRes = await analysisApi.analyzeInspection(inspectionId)
      setActionSuccess(
        `AI Analysis started: ${batchRes.enqueued} photos enqueued for processing (${batchRes.skipped} skipped).`,
      )
      if (images.length > 0) {
        fetchAnalysisForImages(images)
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Failed to start batch AI analysis for this inspection.',
      )
    } finally {
      setAnalyzingAll(false)
    }
  }

  const canUpload =
    role === 'admin' ||
    role === 'manager' ||
    role === 'civil_engineer' ||
    (role === 'inspector' && inspection?.inspector_id === user?.user_id)

  const canReprocessAll = role === 'admin' || role === 'civil_engineer'

  // Analyze button enabled for admin, manager, civil_engineer and inspector who owns the inspection
  const canBatchAnalyze =
    role === 'admin' ||
    role === 'manager' ||
    role === 'civil_engineer' ||
    (role === 'inspector' && inspection?.inspector_id === user?.user_id)

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
            {/* Analyze button: visible to admin, civil_engineer and the inspector who uploaded/owns */}
            {images.length > 0 && (
              <button
                onClick={handleAnalyzeAll}
                disabled={!canBatchAnalyze || analyzingAll}
                title={
                  !canBatchAnalyze
                    ? 'AI analysis requires Admin, Civil Engineer, or assigned Inspector privileges'
                    : undefined
                }
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs transition-colors flex items-center space-x-1.5 ${
                  canBatchAnalyze
                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed opacity-75'
                }`}
              >
                <span>🤖</span>
                <span>
                  {analyzingAll ? 'Starting AI Pipeline...' : 'Run AI Analysis (All)'}
                </span>
              </button>
            )}

            {canReprocessAll && images.length > 0 && (
              <button
                onClick={handlePreprocessAll}
                disabled={reprocessingAll}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors flex items-center space-x-1"
              >
                <span>{reprocessingAll ? 'Processing All...' : '⚡ Re-run Pipeline (All)'}</span>
              </button>
            )}

            {canUpload && (
              <Link
                to="/upload"
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
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
          <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-12 text-center text-sm text-slate-500 animate-pulse">
            Loading inspection and images...
          </div>
        ) : !inspection ? (
          <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-12 text-center text-sm text-slate-500">
            Inspection not found.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header info */}
            <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6">
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

            {/* Aggregate Inspection Damage Severity Summary Card */}
            <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-5">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center space-x-4">
                  <div className="flex flex-col items-start">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Aggregate Damage Severity
                    </span>
                    <div className="flex items-center space-x-2 mt-1">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border shadow-2xs ${getSeverityBadgeClass(
                          inspectionSeverity?.worst_severity || 'none',
                        )}`}
                      >
                        Worst: {inspectionSeverity?.worst_severity || 'none'}
                      </span>
                      <span className="text-xs text-slate-500">
                        Score: <strong>{inspectionSeverity?.worst_score?.toFixed(1) || '0.0'}</strong>
                      </span>
                    </div>
                  </div>

                  <div className="border-l border-slate-200 pl-4 py-1">
                    <p className="text-xs font-medium text-slate-700">
                      Images Assessed: <strong>{inspectionSeverity?.images_assessed || 0}</strong> / {images.length}
                    </p>
                    <p className="text-xs font-medium text-slate-600 mt-0.5">
                      Awaiting Engineer Review:{' '}
                      <strong
                        className={
                          (inspectionSeverity?.images_pending_review || 0) > 0
                            ? 'text-amber-600 font-bold'
                            : 'text-emerald-600 font-semibold'
                        }
                      >
                        {inspectionSeverity?.images_pending_review || 0}
                      </strong>
                    </p>
                  </div>
                </div>

                <div className="text-left sm:text-right sm:max-w-md">
                  <p className="text-[11px] text-slate-500 italic">
                    "Advisory result for engineer review. Not a structural safety verdict. Inspection severity reflects the worst defect level among assessed photos."
                  </p>
                </div>
              </div>
            </div>

            {/* Image Gallery */}
            <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Inspection Photo Gallery
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Click any analyzed photo to inspect bounding boxes and crack geometry metrics.
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
                    const isAnalyzingThis = analyzingImageId === img.image_id
                    const analysisRun = analysisMap[img.image_id]

                    const canUserReprocess =
                      role === 'admin' ||
                      role === 'civil_engineer' ||
                      img.uploaded_by === user?.user_id

                    return (
                      <div
                        key={img.image_id}
                        className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs flex flex-col transition hover:shadow-md"
                      >
                        {/* Toggle header between Original and Processed + Badges */}
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
                                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
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
                                  ? 'bg-white text-indigo-700 shadow-2xs font-semibold'
                                  : 'text-slate-500 hover:text-slate-800'
                              }`}
                            >
                              <span>Enhanced</span>
                              {img.preprocess_status === 'done' && (
                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                              )}
                            </button>
                          </div>

                          {/* AI Analysis & Severity Badges */}
                          <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                            {severityMap[img.image_id] && (
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border shadow-2xs ${getSeverityBadgeClass(
                                  severityMap[img.image_id]?.final_severity ||
                                    severityMap[img.image_id]?.severity_level,
                                )}`}
                              >
                                {severityMap[img.image_id]?.final_severity
                                  ? `Final: ${severityMap[img.image_id]?.final_severity}`
                                  : `Advisory: ${severityMap[img.image_id]?.severity_level}`}
                              </span>
                            )}
                            {!analysisRun && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-200 text-slate-600">
                                Not Analyzed
                              </span>
                            )}
                            {analysisRun &&
                              (analysisRun.status === 'pending' ||
                                analysisRun.status === 'in_progress') && (
                                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 flex items-center space-x-1 animate-pulse">
                                  <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
                                  <span>Analyzing...</span>
                                </span>
                              )}
                            {analysisRun && analysisRun.status === 'done' && !severityMap[img.image_id] && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 flex items-center space-x-1">
                                <span>✓</span>
                                <span>Done</span>
                              </span>
                            )}
                            {analysisRun && analysisRun.status === 'failed' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-800">
                                Failed
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Image Viewer Container (Click to open results if analyzed) */}
                        <div
                          onClick={() => {
                            if (analysisRun && analysisRun.status === 'done') {
                              setSelectedForModal({ image: img, analysis: analysisRun })
                            }
                          }}
                          className={`h-56 w-full bg-slate-900 flex items-center justify-center overflow-hidden relative ${
                            analysisRun && analysisRun.status === 'done'
                              ? 'cursor-pointer group'
                              : ''
                          }`}
                        >
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
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase shadow-xs ${
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
                          <div className="absolute bottom-2 left-2 bg-slate-900/80 px-2 py-0.5 rounded text-[10px] font-medium text-slate-200 backdrop-blur-2xs">
                            {currentTab === 'original' ? 'Original' : 'Enhanced'}
                          </div>

                          {/* Hover tooltip for analyzed images */}
                          {analysisRun && analysisRun.status === 'done' && (
                            <div className="absolute inset-0 bg-indigo-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
                              <span className="px-3 py-1.5 bg-white text-indigo-900 rounded-lg text-xs font-bold shadow-lg">
                                🔍 Open AI Results Viewer
                              </span>
                            </div>
                          )}
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
                            </div>

                            {/* AI Summary Banner if Done */}
                            {analysisRun && analysisRun.status === 'done' && (
                              <div className="mt-2.5 p-2 bg-indigo-50/60 rounded-lg border border-indigo-100 text-[11px] space-y-0.5">
                                <div className="flex justify-between text-indigo-900 font-semibold">
                                  <span>Detections:</span>
                                  <span>{analysisRun.detections.length} damages</span>
                                </div>
                                {analysisRun.crack_measurement && (
                                  <div className="flex justify-between text-indigo-800 text-[10px]">
                                    <span>Crack Length:</span>
                                    <span className="font-mono">
                                      {analysisRun.crack_measurement.length_px.toFixed(1)} px
                                    </span>
                                  </div>
                                )}
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
                          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2 text-[11px]">
                            {/* Single image Analyze button: enabled for admin, civil_engineer, and uploader */}
                            {(() => {
                              const canAnalyzeSingle =
                                role === 'admin' ||
                                role === 'civil_engineer' ||
                                (role === 'inspector' && img.uploaded_by === user?.user_id)

                              return (
                                <button
                                  onClick={() => handleAnalyzeSingle(img.image_id)}
                                  disabled={
                                    !canAnalyzeSingle ||
                                    isAnalyzingThis ||
                                    img.quality_status === 'rejected'
                                  }
                                  title={
                                    !canAnalyzeSingle
                                      ? 'Requires Admin, Civil Engineer, or image uploader privileges'
                                      : img.quality_status === 'rejected'
                                      ? 'Rejected images cannot be analyzed'
                                      : undefined
                                  }
                                  className={`font-semibold flex items-center space-x-1 ${
                                    canAnalyzeSingle && img.quality_status !== 'rejected'
                                      ? 'text-indigo-600 hover:text-indigo-800 cursor-pointer'
                                      : 'text-slate-400 cursor-not-allowed'
                                  }`}
                                >
                                  <span>⚡</span>
                                  <span>
                                    {isAnalyzingThis
                                      ? 'Enqueuing...'
                                      : analysisRun?.status === 'done'
                                      ? 'Re-analyze'
                                      : 'Analyze'}
                                  </span>
                                </button>
                              )
                            })()}

                            {/* View Results Button */}
                            {analysisRun && analysisRun.status === 'done' && (
                              <button
                                onClick={() =>
                                  setSelectedForModal({ image: img, analysis: analysisRun })
                                }
                                className="px-2 py-0.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded text-[11px] transition-colors"
                              >
                                View Results
                              </button>
                            )}

                            {/* Preprocess Single Button */}
                            {canUserReprocess && (
                              <button
                                onClick={() => handlePreprocessSingle(img.image_id)}
                                disabled={isReprocessingThis}
                                className="text-slate-500 hover:text-slate-800 disabled:opacity-50"
                                title="Re-run Preprocessing"
                              >
                                {isReprocessingThis ? '...' : '🔄 Enhance'}
                              </button>
                            )}

                            {/* Delete button */}
                            {(role === 'admin' ||
                              role === 'civil_engineer' ||
                              img.uploaded_by === user?.user_id) &&
                              inspection.status !== 'completed' && (
                                <button
                                  onClick={() => handleDeleteImage(img.image_id)}
                                  className="text-rose-500 hover:text-rose-700 font-semibold ml-auto"
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

      {/* Analysis Results Modal */}
      {selectedForModal && (
        <AnalysisModal
          isOpen={!!selectedForModal}
          onClose={() => {
            setSelectedForModal(null)
            fetchData()
          }}
          image={selectedForModal.image}
          analysis={selectedForModal.analysis}
          asset={asset}
          onAnalysisUpdated={(updated) => {
            setAnalysisMap((prev) => ({ ...prev, [updated.image_id]: updated }))
            setSelectedForModal((prev) => (prev ? { ...prev, analysis: updated } : null))
            fetchData()
          }}
        />
      )}
    </div>
  )
}

export default InspectionDetailPage
