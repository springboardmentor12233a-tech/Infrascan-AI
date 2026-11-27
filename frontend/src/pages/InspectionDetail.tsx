import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { AuthenticatedImage, type ImageViewMode } from '../components/AuthenticatedImage'
import { useAuth } from '../context/AuthContext'
import {
  imagesApi,
  inspectionsApi,
  analysisApi,
  progressionApi,
  reportsApi,
  type ImageMetadata,
  type Inspection,
  type DamageAssessment,
  type DamageProgression,
  type InspectionReport,
} from '../api/client'

export const InspectionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user, role } = useAuth()

  const [inspection, setInspection] = useState<Inspection | null>(null)
  const [allInspections, setAllInspections] = useState<Inspection[]>([])
  const [images, setImages] = useState<ImageMetadata[]>([])
  const [assessments, setAssessments] = useState<Record<number, DamageAssessment>>({})
  const [summary, setSummary] = useState<any | null>(null)
  const [reports, setReports] = useState<InspectionReport[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Track per-image view mode: 'original' | 'processed' | 'mask' | 'heatmap'
  const [viewModeMap, setViewModeMap] = useState<Record<number, ImageViewMode>>({})
  // Track ongoing analysis / processing
  const [analyzingMap, setAnalyzingMap] = useState<Record<number, boolean>>({})
  const [analyzingAll, setAnalyzingAll] = useState(false)
  const [reprocessingAll, setReprocessingAll] = useState(false)
  const [generatingReport, setGeneratingReport] = useState<string | null>(null)

  // Progression comparison modal/section
  const [compareInspectionId, setCompareInspectionId] = useState<number | ''>('')
  const [progressionData, setProgressionData] = useState<DamageProgression | null>(null)
  const [progressionLoading, setProgressionLoading] = useState(false)

  const inspectionId = id ? parseInt(id, 10) : 0

  const fetchData = async () => {
    if (!inspectionId) return
    try {
      setLoading(true)
      setError(null)

      const [inspData, imgsData, reportsData] = await Promise.all([
        inspectionsApi.getById(inspectionId),
        imagesApi.listByInspection(inspectionId),
        reportsApi.list(inspectionId).catch(() => []),
      ])

      setInspection(inspData)
      setImages(imgsData)
      setReports(reportsData)

      // Fetch summary and assessments for photos
      try {
        const sumData = await analysisApi.getInspectionSummary(inspectionId)
        setSummary(sumData)
      } catch {
        // Summary might be empty if no analysis has run yet
      }

      // Fetch existing assessments for images
      const assessMap: Record<number, DamageAssessment> = {}
      await Promise.all(
        imgsData.map(async (img) => {
          try {
            const assess = await analysisApi.getAssessment(img.image_id)
            if (assess) {
              assessMap[img.image_id] = assess
            }
          } catch {
            // No assessment for this image yet
          }
        }),
      )
      setAssessments(assessMap)

      // Also fetch list of inspections for asset to enable progression comparison
      if (inspData.asset_id) {
        try {
          const list = await inspectionsApi.list({ asset_id: inspData.asset_id })
          const past = list.filter((i) => i.inspection_id !== inspectionId)
          setAllInspections(past)
          if (past.length > 0 && !compareInspectionId) {
            setCompareInspectionId(past[0].inspection_id)
          }
        } catch {
          // Ignore
        }
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Failed to load inspection workspace.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [inspectionId])

  // Run AI Damage Analysis on a single photo
  const handleAnalyzeSingle = async (imageId: number) => {
    try {
      setAnalyzingMap((prev) => ({ ...prev, [imageId]: true }))
      setError(null)
      setActionSuccess(null)

      const assess = await analysisApi.analyzeImage(imageId)
      setAssessments((prev) => ({ ...prev, [imageId]: assess }))
      // Switch view to Grad-CAM heatmap or mask to show user instant insight
      setViewModeMap((prev) => ({ ...prev, [imageId]: 'heatmap' }))
      setActionSuccess(`AI Damage assessment completed for photo #${imageId}.`)

      // Refresh summary
      const sumData = await analysisApi.getInspectionSummary(inspectionId)
      setSummary(sumData)
    } catch (err: any) {
      setError(err.response?.data?.detail || `Analysis failed for image #${imageId}.`)
    } finally {
      setAnalyzingMap((prev) => ({ ...prev, [imageId]: false }))
    }
  }

  // Run AI Damage Analysis on ALL photos in this inspection
  const handleAnalyzeAll = async () => {
    if (images.length === 0) return
    try {
      setAnalyzingAll(true)
      setError(null)
      setActionSuccess(null)

      let count = 0
      for (const img of images) {
        try {
          const assess = await analysisApi.analyzeImage(img.image_id)
          setAssessments((prev) => ({ ...prev, [img.image_id]: assess }))
          setViewModeMap((prev) => ({ ...prev, [img.image_id]: 'heatmap' }))
          count++
        } catch {
          // Continue with next
        }
      }

      const sumData = await analysisApi.getInspectionSummary(inspectionId)
      setSummary(sumData)
      setActionSuccess(`AI Damage Assessment successfully executed on ${count} inspection photos!`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete batch damage analysis.')
    } finally {
      setAnalyzingAll(false)
    }
  }

  // Preprocess all photos (CLAHE)
  const handlePreprocessAll = async () => {
    try {
      setReprocessingAll(true)
      setError(null)
      setActionSuccess(null)
      const updatedList = await imagesApi.preprocessInspection(inspectionId)
      setImages(updatedList)
      setActionSuccess(`Enhancement pipeline completed for ${updatedList.length} photos.`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to preprocess images.')
    } finally {
      setReprocessingAll(false)
    }
  }

  // Generate Report (PDF, CSV, JSON)
  const handleGenerateReport = async (format: 'pdf' | 'csv' | 'json') => {
    try {
      setGeneratingReport(format)
      setError(null)
      setActionSuccess(null)

      const report = await reportsApi.generate(inspectionId, format)
      setActionSuccess(`Formal ${format.toUpperCase()} inspection report generated successfully!`)
      // Refresh reports list
      const updatedReports = await reportsApi.list(inspectionId)
      setReports(updatedReports)

      // Trigger instant download
      await reportsApi.downloadFile(report.report_id, `Inspection_${inspectionId}_Report.${format}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to generate ${format.toUpperCase()} report.`)
    } finally {
      setGeneratingReport(null)
    }
  }

  // Compare progression
  const handleRunProgression = async () => {
    if (!compareInspectionId) return
    try {
      setProgressionLoading(true)
      setError(null)
      const prog = await progressionApi.compare(inspectionId, Number(compareInspectionId))
      setProgressionData(prog)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to calculate damage progression.')
    } finally {
      setProgressionLoading(false)
    }
  }

  const canUpload =
    role === 'admin' ||
    role === 'civil_engineer' ||
    (role === 'inspector' && inspection?.inspector_id === user?.user_id)

  const canAnalyze = role === 'admin' || role === 'civil_engineer' || role === 'inspector'

  const getSeverityBadgeClass = (sev?: string) => {
    switch (sev) {
      case 'critical':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
      case 'severe':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
      case 'moderate':
        return 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
      case 'minor':
        return 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
      default:
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
    }
  }

  return (
    <div className="min-h-screen bg-[#141619] text-[#FFFFFF] flex flex-col font-sans selection:bg-[#0A21C0] selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Top Navigation & Breadcrumbs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <Link
            to="/inspections"
            className="text-xs font-semibold text-[#B3B4BD] hover:text-white flex items-center space-x-2 transition-colors group"
          >
            <span className="text-[#0A21C0] group-hover:-translate-x-0.5 transition-transform">&larr;</span>
            <span>Back to Inspections Registry</span>
          </Link>

          {/* Quick Action Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {images.length > 0 && (
              <button
                onClick={handleAnalyzeAll}
                disabled={analyzingAll}
                className="px-4 py-2 bg-[#0A21C0] hover:bg-[#081ba0] disabled:opacity-50 text-white rounded-full text-xs font-semibold shadow-lg shadow-[#0A21C0]/30 transition-all flex items-center space-x-1.5 cursor-pointer"
              >
                <span>{analyzingAll ? '⚡ Analyzing Entire Inspection...' : '⚡ Run AI Damage Assessment (All)'}</span>
              </button>
            )}

            {images.length > 0 && (
              <button
                onClick={handlePreprocessAll}
                disabled={reprocessingAll}
                className="px-3.5 py-2 bg-[#2C2E3A] hover:bg-[#393b4a] text-white border border-[#2C2E3A] hover:border-[#0A21C0]/40 rounded-full text-xs font-medium transition-all"
              >
                <span>{reprocessingAll ? 'Enhancing...' : '🔄 Enhance Photos (CLAHE)'}</span>
              </button>
            )}

            {canUpload && inspection?.status !== 'completed' && (
              <Link
                to="/upload"
                className="px-4 py-2 bg-[#050A44] hover:bg-[#08116b] text-[#B3B4BD] hover:text-white border border-[#0A21C0]/40 rounded-full text-xs font-semibold transition-all flex items-center space-x-1"
              >
                <span>+ Upload Photos</span>
              </Link>
            )}
          </div>
        </div>

        {/* Status Alerts */}
        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-rose-300 text-sm rounded-xl flex items-center justify-between backdrop-blur-md">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white font-bold ml-4">&times;</button>
          </div>
        )}

        {actionSuccess && (
          <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-sm rounded-xl flex items-center justify-between backdrop-blur-md">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-white font-bold ml-4">&times;</button>
          </div>
        )}

        {loading ? (
          <div className="bg-[#2C2E3A]/60 rounded-2xl border border-[#2C2E3A] p-12 text-center text-sm text-[#B3B4BD] animate-pulse">
            <div className="w-8 h-8 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            Loading inspection analytics and photo models...
          </div>
        ) : !inspection ? (
          <div className="bg-[#2C2E3A]/60 rounded-2xl border border-[#2C2E3A] p-12 text-center text-sm text-[#B3B4BD]">
            Inspection not found in registry.
          </div>
        ) : (
          <>
            {/* INSPECTION METADATA & HERO CARD */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-96 h-96 bg-[#0A21C0]/10 rounded-full blur-3xl pointer-events-none"></div>

              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-[#141619]/60">
                <div>
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="font-mono text-xs font-bold text-[#0A21C0] uppercase tracking-wider bg-[#050A44] px-2.5 py-1 rounded-md border border-[#0A21C0]/30">
                      INSPECTION #{inspection.inspection_id}
                    </span>
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                        inspection.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : inspection.status === 'in_progress'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-[#050A44] text-[#B3B4BD] border border-[#2C2E3A]'
                      }`}
                    >
                      {inspection.status.replace('_', ' ')}
                    </span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {inspection.asset_name || `Asset #${inspection.asset_id}`}
                  </h1>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                  <div className="bg-[#141619]/60 p-3 rounded-xl border border-[#2C2E3A]">
                    <div className="text-[#B3B4BD] uppercase font-mono text-[10px]">Scheduled Date</div>
                    <div className="text-white font-semibold mt-1">
                      {new Date(inspection.inspection_date).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="bg-[#141619]/60 p-3 rounded-xl border border-[#2C2E3A]">
                    <div className="text-[#B3B4BD] uppercase font-mono text-[10px]">Field Inspector</div>
                    <div className="text-white font-semibold mt-1 truncate">
                      {inspection.inspector_name || `ID #${inspection.inspector_id}`}
                    </div>
                  </div>
                  <div className="bg-[#141619]/60 p-3 rounded-xl border border-[#2C2E3A] col-span-2 sm:col-span-1">
                    <div className="text-[#B3B4BD] uppercase font-mono text-[10px]">Photos Captured</div>
                    <div className="text-white font-semibold mt-1">
                      {images.length} High-Res Images
                    </div>
                  </div>
                </div>
              </div>

              {/* OVERALL DAMAGE ASSESSMENT SUMMARY (IF ASSESSED) */}
              {summary && summary.total_assessments > 0 ? (
                <div className="mt-6 pt-2 grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-[#050A44]/40 p-4 rounded-xl border border-[#0A21C0]/30 flex flex-col justify-between">
                    <div className="text-xs text-[#B3B4BD] uppercase tracking-wider font-semibold">
                      Structural Health Severity
                    </div>
                    <div className="my-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${getSeverityBadgeClass(summary.overall_severity)}`}>
                        {summary.overall_severity?.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-[11px] text-[#B3B4BD]">
                      Based on worst-case structural defect
                    </div>
                  </div>

                  <div className="bg-[#050A44]/40 p-4 rounded-xl border border-[#0A21C0]/30 flex flex-col justify-between">
                    <div className="text-xs text-[#B3B4BD] uppercase tracking-wider font-semibold">
                      Max Severity Score
                    </div>
                    <div className="text-2xl font-black text-white my-1">
                      {summary.max_severity_score?.toFixed(1) || '0.0'}
                      <span className="text-xs font-normal text-[#B3B4BD]"> / 100</span>
                    </div>
                    <div className="w-full bg-[#141619] rounded-full h-2 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 transition-all duration-500"
                        style={{ width: `${Math.min(100, summary.max_severity_score || 0)}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="bg-[#050A44]/40 p-4 rounded-xl border border-[#0A21C0]/30 flex flex-col justify-between">
                    <div className="text-xs text-[#B3B4BD] uppercase tracking-wider font-semibold">
                      Dominant Defect Type
                    </div>
                    <div className="text-base font-bold text-white capitalize my-1 truncate">
                      {summary.dominant_defect ? summary.dominant_defect.replace('_', ' ') : 'None Detected'}
                    </div>
                    <div className="text-[11px] text-[#B3B4BD]">
                      {summary.total_assessments} image(s) analyzed by YOLO
                    </div>
                  </div>

                  <div className="bg-[#050A44]/40 p-4 rounded-xl border border-[#0A21C0]/30 flex flex-col justify-between">
                    <div className="text-xs text-[#B3B4BD] uppercase tracking-wider font-semibold">
                      Remediation Action
                    </div>
                    <div className="text-xs text-[#B3B4BD] line-clamp-2 my-1">
                      {summary.recommended_action || 'No immediate action required.'}
                    </div>
                    <div className="text-[10px] text-[#0A21C0] font-semibold">
                      Automated Engineering Guideline
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-6 p-4 bg-[#141619]/60 rounded-xl border border-dashed border-[#2C2E3A] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#B3B4BD]">
                  <div>
                    <span className="font-semibold text-white">Damage Analysis Pending: </span>
                    Run the multi-model AI pipeline to compute U-Net crack masks, morphological metrics, and severity scores.
                  </div>
                  {canAnalyze && images.length > 0 && (
                    <button
                      onClick={handleAnalyzeAll}
                      disabled={analyzingAll}
                      className="px-4 py-2 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full font-semibold shadow-lg shadow-[#0A21C0]/30 cursor-pointer shrink-0"
                    >
                      Analyze All Photos Now
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* AUTOMATED REPORT GENERATION TOOLBAR */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                  <span>📄 Automated Inspection Reports</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#0A21C0]/30 text-blue-300">
                    Milestone 4
                  </span>
                </h2>
                <p className="text-xs text-[#B3B4BD] mt-1">
                  Export formal civil engineering reports complete with defect tables, severity index, and signoff.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => handleGenerateReport('pdf')}
                  disabled={generatingReport !== null}
                  className="px-4 py-2.5 bg-[#0A21C0] hover:bg-[#081ba0] disabled:opacity-50 text-white rounded-full text-xs font-semibold shadow-md shadow-[#0A21C0]/30 transition-all flex items-center space-x-2 cursor-pointer"
                >
                  <span>{generatingReport === 'pdf' ? 'Generating PDF...' : '📥 Download PDF Report'}</span>
                </button>

                <button
                  onClick={() => handleGenerateReport('csv')}
                  disabled={generatingReport !== null}
                  className="px-4 py-2.5 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-white rounded-full text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer"
                >
                  <span>{generatingReport === 'csv' ? 'Generating CSV...' : '📊 Export CSV Data'}</span>
                </button>

                <button
                  onClick={() => handleGenerateReport('json')}
                  disabled={generatingReport !== null}
                  className="px-4 py-2.5 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-white rounded-full text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer"
                >
                  <span>{generatingReport === 'json' ? 'Generating JSON...' : '⚙️ Export JSON'}</span>
                </button>
              </div>
            </div>

            {/* PREVIOUSLY GENERATED REPORTS LIST */}
            {reports.length > 0 && (
              <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
                  Generated Report Archives ({reports.length})
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {reports.map((rep) => (
                    <div
                      key={rep.report_id}
                      className="bg-[#141619] p-3 rounded-xl border border-[#2C2E3A] flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="font-semibold text-white uppercase">
                          {rep.report_format} Document #{rep.report_id}
                        </div>
                        <div className="text-[10px] text-[#B3B4BD]">
                          Condition Score: {rep.overall_condition_score}/100 &bull; {(rep.file_size_bytes / 1024).toFixed(1)} KB
                        </div>
                      </div>
                      <button
                        onClick={() => reportsApi.downloadFile(rep.report_id, `report_${rep.report_id}.${rep.report_format}`)}
                        className="px-3 py-1 bg-[#0A21C0]/30 hover:bg-[#0A21C0] text-blue-300 hover:text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                      >
                        Download
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* MULTI-TEMPORAL DAMAGE PROGRESSION PANEL */}
            {allInspections.length > 0 && (
              <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#141619]/60">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                      <span>📈 Multi-Temporal Damage Progression Tracking</span>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#0A21C0]/30 text-blue-300">
                        Milestone 3
                      </span>
                    </h2>
                    <p className="text-xs text-[#B3B4BD] mt-1">
                      Quantify crack propagation rate, width growth, and deterioration trend against historical inspections.
                    </p>
                  </div>

                  <div className="flex items-center space-x-3">
                    <select
                      value={compareInspectionId}
                      onChange={(e) => setCompareInspectionId(Number(e.target.value))}
                      className="px-3 py-1.5 bg-[#141619] border border-[#2C2E3A] rounded-xl text-xs text-white focus:outline-none focus:border-[#0A21C0]"
                    >
                      {allInspections.map((insp) => (
                        <option key={insp.inspection_id} value={insp.inspection_id}>
                          Compare with #{insp.inspection_id} ({new Date(insp.inspection_date).toLocaleDateString()})
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={handleRunProgression}
                      disabled={progressionLoading || !compareInspectionId}
                      className="px-4 py-1.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
                    >
                      {progressionLoading ? 'Calculating...' : 'Compare'}
                    </button>
                  </div>
                </div>

                {progressionData && (
                  <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                    <div className="bg-[#141619] p-4 rounded-xl border border-[#2C2E3A]">
                      <div className="text-[#B3B4BD] font-mono text-[10px] uppercase">Deterioration Trend</div>
                      <div className="text-base font-bold text-white capitalize mt-1">
                        {progressionData.deterioration_trend}
                      </div>
                      <div className="text-[10px] text-[#B3B4BD] mt-1">
                        Interval: {progressionData.days_between} days between scans
                      </div>
                    </div>

                    <div className="bg-[#141619] p-4 rounded-xl border border-[#2C2E3A]">
                      <div className="text-[#B3B4BD] font-mono text-[10px] uppercase">Growth Rate</div>
                      <div className="text-base font-bold text-white mt-1">
                        {progressionData.growth_rate_pct > 0 ? `+${progressionData.growth_rate_pct}%` : `${progressionData.growth_rate_pct}%`}
                      </div>
                      <div className="text-[10px] text-[#B3B4BD] mt-1">
                        Normalized structural expansion
                      </div>
                    </div>

                    <div className="bg-[#141619] p-4 rounded-xl border border-[#2C2E3A]">
                      <div className="text-[#B3B4BD] font-mono text-[10px] uppercase">Δ Crack Length</div>
                      <div className="text-base font-bold text-white mt-1">
                        {progressionData.length_change_px > 0 ? `+${progressionData.length_change_px} px` : `${progressionData.length_change_px} px`}
                      </div>
                      <div className="text-[10px] text-[#B3B4BD] mt-1">
                        Net skeleton length variation
                      </div>
                    </div>

                    <div className="bg-[#141619] p-4 rounded-xl border border-[#2C2E3A]">
                      <div className="text-[#B3B4BD] font-mono text-[10px] uppercase">Δ Max Crack Width</div>
                      <div className="text-base font-bold text-white mt-1">
                        {progressionData.max_width_change_px > 0 ? `+${progressionData.max_width_change_px} px` : `${progressionData.max_width_change_px} px`}
                      </div>
                      <div className="text-[10px] text-[#B3B4BD] mt-1">
                        Euclidean distance transform change
                      </div>
                    </div>

                    <div className="sm:col-span-2 md:col-span-4 bg-[#050A44]/30 p-3 rounded-xl border border-[#0A21C0]/30 text-[#B3B4BD]">
                      <span className="font-semibold text-white">Summary Finding: </span>
                      {progressionData.summary}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* INSPECTION PHOTO GALLERY & AI ANALYSIS WORKSPACE */}
            <div className="bg-[#2C2E3A] rounded-2xl border border-[#2C2E3A] p-6 shadow-xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Inspection Photos & AI Defect Workspace
                  </h2>
                  <p className="text-xs text-[#B3B4BD] mt-1">
                    Multi-layer visualization: Original, CLAHE Enhanced, U-Net Segmentation Mask, and Explainable Grad-CAM Heatmap.
                  </p>
                </div>
                <div className="text-xs text-[#B3B4BD]">
                  {images.length} Photo(s) &bull; {Object.keys(assessments).length} Analyzed
                </div>
              </div>

              {images.length === 0 ? (
                <div className="p-12 text-center text-xs text-[#B3B4BD] bg-[#141619] rounded-2xl border border-dashed border-[#2C2E3A]">
                  <p className="mb-4 text-sm font-medium">No inspection photos uploaded yet.</p>
                  {canUpload && (
                    <Link
                      to="/upload"
                      className="px-5 py-2.5 bg-[#0A21C0] hover:bg-[#081ba0] text-white rounded-full font-semibold inline-block shadow-lg shadow-[#0A21C0]/30"
                    >
                      Upload First Photo
                    </Link>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {images.map((img) => {
                    const currentMode = viewModeMap[img.image_id] || 'original'
                    const assess = assessments[img.image_id]
                    const isAnalyzingThis = analyzingMap[img.image_id]

                    return (
                      <div
                        key={img.image_id}
                        className="bg-[#141619] rounded-2xl border border-[#2C2E3A] hover:border-[#0A21C0]/40 overflow-hidden shadow-lg flex flex-col transition-all duration-300"
                      >
                        {/* 4-WAY LAYER TOGGLE HEADER */}
                        <div className="bg-[#141619]/90 p-2 border-b border-[#2C2E3A] flex items-center justify-between text-xs">
                          <div className="flex flex-wrap gap-1">
                            <button
                              onClick={() => setViewModeMap((prev) => ({ ...prev, [img.image_id]: 'original' }))}
                              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                                currentMode === 'original'
                                  ? 'bg-[#0A21C0] text-white shadow-sm'
                                  : 'text-[#B3B4BD] hover:text-white'
                              }`}
                            >
                              Original
                            </button>
                            <button
                              onClick={() => setViewModeMap((prev) => ({ ...prev, [img.image_id]: 'processed' }))}
                              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                                currentMode === 'processed'
                                  ? 'bg-[#0A21C0] text-white shadow-sm'
                                  : 'text-[#B3B4BD] hover:text-white'
                              }`}
                            >
                              Enhanced (CLAHE)
                            </button>
                            <button
                              onClick={() => setViewModeMap((prev) => ({ ...prev, [img.image_id]: 'mask' }))}
                              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                                currentMode === 'mask'
                                  ? 'bg-[#0A21C0] text-white shadow-sm'
                                  : 'text-[#B3B4BD] hover:text-white'
                              }`}
                            >
                              U-Net Mask
                            </button>
                            <button
                              onClick={() => setViewModeMap((prev) => ({ ...prev, [img.image_id]: 'heatmap' }))}
                              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                                currentMode === 'heatmap'
                                  ? 'bg-[#0A21C0] text-white shadow-sm'
                                  : 'text-[#B3B4BD] hover:text-white'
                              }`}
                            >
                              Grad-CAM Heatmap
                            </button>
                          </div>

                          {/* Quality Status Pill */}
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              img.quality_status === 'passed'
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : img.quality_status === 'warning'
                                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            }`}
                          >
                            {img.quality_status}
                          </span>
                        </div>

                        {/* IMAGE VIEWER CANVAS */}
                        <div className="h-72 w-full bg-[#050A44]/20 flex items-center justify-center overflow-hidden relative">
                          <AuthenticatedImage
                            imageId={img.image_id}
                            alt={img.original_filename}
                            mode={currentMode}
                            className="max-h-full max-w-full object-contain"
                          />

                          {/* Mode Banner Indicator */}
                          <div className="absolute bottom-2 left-2 bg-[#141619]/90 px-2.5 py-1 rounded-md text-[10px] font-mono font-medium text-[#B3B4BD] border border-[#2C2E3A] backdrop-blur-md">
                            Viewing: {currentMode.toUpperCase()} Layer
                          </div>

                          {/* Severity Pill Overlay if assessment exists */}
                          {assess && (
                            <div className="absolute top-2 right-2">
                              <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-lg ${getSeverityBadgeClass(assess.severity_category)}`}>
                                {assess.severity_category.replace('_', ' ')} ({assess.severity_score}/100)
                              </span>
                            </div>
                          )}
                        </div>

                        {/* METADATA & AI FINDINGS PANEL */}
                        <div className="p-5 flex-1 flex flex-col justify-between text-xs space-y-4">
                          <div>
                            <div className="flex items-center justify-between">
                              <div className="font-bold text-white text-sm truncate" title={img.original_filename}>
                                {img.original_filename}
                              </div>
                              <div className="text-[10px] text-[#B3B4BD] font-mono">
                                {img.width_px} x {img.height_px} px &bull; {(img.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                              </div>
                            </div>

                            {/* DAMAGE ASSESSMENT SECTION */}
                            {assess ? (
                              <div className="mt-4 p-4 bg-[#2C2E3A]/60 rounded-xl border border-[#2C2E3A] space-y-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <span className="font-semibold text-white capitalize text-sm">
                                      {assess.defect_type.replace('_', ' ')}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#0A21C0]/30 text-blue-300">
                                      {(assess.confidence * 100).toFixed(1)}% Confidence
                                    </span>
                                  </div>
                                  <div className="text-[11px] font-bold text-white font-mono">
                                    Severity: {assess.severity_score}/100
                                  </div>
                                </div>

                                {/* Crack Geometry Grid */}
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-2 border-t border-[#141619]">
                                  <div className="bg-[#141619] p-2 rounded-lg">
                                    <div className="text-[#B3B4BD] text-[9px] uppercase font-mono">Length</div>
                                    <div className="font-semibold text-white mt-0.5">
                                      {assess.crack_length_mm ? `${assess.crack_length_mm.toFixed(1)} mm` : `${assess.crack_length_px} px`}
                                    </div>
                                  </div>

                                  <div className="bg-[#141619] p-2 rounded-lg">
                                    <div className="text-[#B3B4BD] text-[9px] uppercase font-mono">Max Width</div>
                                    <div className="font-semibold text-white mt-0.5">
                                      {assess.max_width_mm ? `${assess.max_width_mm.toFixed(1)} mm` : `${assess.max_width_px} px`}
                                    </div>
                                  </div>

                                  <div className="bg-[#141619] p-2 rounded-lg">
                                    <div className="text-[#B3B4BD] text-[9px] uppercase font-mono">Density</div>
                                    <div className="font-semibold text-white mt-0.5">
                                      {assess.crack_density_percent?.toFixed(2) || '0.00'}%
                                    </div>
                                  </div>

                                  <div className="bg-[#141619] p-2 rounded-lg">
                                    <div className="text-[#B3B4BD] text-[9px] uppercase font-mono">Orientation</div>
                                    <div className="font-semibold text-white mt-0.5">
                                      {assess.orientation_deg ? `${assess.orientation_deg.toFixed(1)}°` : '0°'}
                                    </div>
                                  </div>
                                </div>

                                {assess.recommended_action && (
                                  <div className="text-[10px] text-[#B3B4BD] bg-[#050A44]/30 p-2 rounded-lg border border-[#0A21C0]/20">
                                    <span className="font-semibold text-blue-300">Remediation: </span>
                                    {assess.recommended_action}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="mt-4 p-3 bg-[#141619] rounded-xl border border-dashed border-[#2C2E3A] text-center text-[#B3B4BD] text-[11px]">
                                No AI assessment performed for this photo yet.
                              </div>
                            )}

                            {/* Image Quality Specs */}
                            <div className="mt-3 flex items-center justify-between text-[11px] text-[#B3B4BD]">
                              <span>Sharpness/Blur: <strong className="text-white font-mono">{img.blur_score.toFixed(1)}</strong></span>
                              <span>Brightness: <strong className="text-white font-mono">{img.brightness_score.toFixed(1)}</strong></span>
                              <span>Source: <strong className="text-white capitalize">{img.source}</strong></span>
                            </div>
                          </div>

                          {/* ACTION BUTTONS FOOTER */}
                          <div className="pt-3 border-t border-[#2C2E3A] flex items-center justify-between">
                            {canAnalyze && (
                              <button
                                onClick={() => handleAnalyzeSingle(img.image_id)}
                                disabled={isAnalyzingThis}
                                className="px-3.5 py-1.5 bg-[#0A21C0] hover:bg-[#081ba0] disabled:opacity-50 text-white rounded-full text-xs font-semibold shadow-md shadow-[#0A21C0]/20 transition-all cursor-pointer"
                              >
                                {isAnalyzingThis ? 'Analyzing...' : '⚡ Run Damage Assessment'}
                              </button>
                            )}

                            {canUpload && inspection.status !== 'completed' && (
                              <button
                                onClick={async () => {
                                  if (window.confirm(`Delete photo #${img.image_id}?`)) {
                                    await imagesApi.delete(img.image_id)
                                    fetchData()
                                  }
                                }}
                                className="text-rose-400 hover:text-rose-300 text-xs font-semibold ml-auto transition-colors cursor-pointer"
                              >
                                Delete Photo
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
          </>
        )}
      </main>
    </div>
  )
}

export default InspectionDetailPage
