import React, { useState, useEffect, useMemo, useRef } from 'react'
import {
  type AnalysisRun,
  type ImageMetadata,
  type SeverityAssessment,
  type InfrastructureAsset,
  type ExplanationItem,
  type CompareMapsResult,
  analysisApi,
  imagesApi,
  severityApi,
  inspectionsApi,
  assetsApi,
  explainApi,
} from '../api/client'
import { useAuth } from '../context/AuthContext'

export interface DefectColor {
  bg: string
  stroke: string
  text: string
  fill: string
  name: string
  category: 'Road Damage' | 'CODEBRIM Bridge Defect' | 'General'
}

export const DEFECT_COLORS: Record<string, DefectColor> = {
  // Road damage classes (RDD2022)
  'D00': { bg: '#3b82f6', stroke: '#3b82f6', text: '#ffffff', fill: 'rgba(59, 130, 246, 0.18)', name: 'D00 Longitudinal Crack', category: 'Road Damage' },
  'D10': { bg: '#6366f1', stroke: '#6366f1', text: '#ffffff', fill: 'rgba(99, 102, 241, 0.18)', name: 'D10 Transverse Crack', category: 'Road Damage' },
  'D20': { bg: '#f59e0b', stroke: '#f59e0b', text: '#ffffff', fill: 'rgba(245, 158, 11, 0.18)', name: 'D20 Alligator Crack', category: 'Road Damage' },
  'D40': { bg: '#ef4444', stroke: '#ef4444', text: '#ffffff', fill: 'rgba(239, 68, 68, 0.18)', name: 'D40 Pothole', category: 'Road Damage' },
  // CODEBRIM defect classes
  'crack': { bg: '#10b981', stroke: '#10b981', text: '#ffffff', fill: 'rgba(168, 85, 247, 0.18)', name: 'Crack', category: 'CODEBRIM Bridge Defect' },
  'spallation': { bg: '#f97316', stroke: '#f97316', text: '#ffffff', fill: 'rgba(249, 115, 22, 0.18)', name: 'Spallation', category: 'CODEBRIM Bridge Defect' },
  'exposed_bars': { bg: '#dc2626', stroke: '#dc2626', text: '#ffffff', fill: 'rgba(220, 38, 38, 0.18)', name: 'Exposed Bars', category: 'CODEBRIM Bridge Defect' },
  'efflorescence': { bg: '#06b6d4', stroke: '#06b6d4', text: '#ffffff', fill: 'rgba(6, 182, 212, 0.18)', name: 'Efflorescence', category: 'CODEBRIM Bridge Defect' },
  'corrosion_stain': { bg: '#a855f7', stroke: '#a855f7', text: '#ffffff', fill: 'rgba(168, 85, 247, 0.18)', name: 'Corrosion Stain', category: 'CODEBRIM Bridge Defect' },
}

export const getDefectColor = (damageType?: string, damageLabel?: string): DefectColor => {
  const norm = `${damageType || ''} ${damageLabel || ''}`.toLowerCase()
  if (norm.includes('d00') || norm.includes('longitudinal')) return DEFECT_COLORS['D00']
  if (norm.includes('d10') || norm.includes('transverse')) return DEFECT_COLORS['D10']
  if (norm.includes('d20') || norm.includes('alligator')) return DEFECT_COLORS['D20']
  if (norm.includes('d40') || norm.includes('pothole')) return DEFECT_COLORS['D40']
  if (norm.includes('spall')) return DEFECT_COLORS['spallation']
  if (norm.includes('exposed') || norm.includes('bar') || norm.includes('rebar')) return DEFECT_COLORS['exposed_bars']
  if (norm.includes('efflor')) return DEFECT_COLORS['efflorescence']
  if (norm.includes('corros')) return DEFECT_COLORS['corrosion_stain']
  if (norm.includes('crack')) return DEFECT_COLORS['crack']
  return { bg: '#64748b', stroke: '#64748b', text: '#ffffff', fill: 'rgba(100, 116, 139, 0.18)', name: damageType || 'Defect', category: 'General' }
}

interface AnalysisModalProps {
  isOpen: boolean
  onClose: () => void
  image: ImageMetadata
  analysis: AnalysisRun
  asset?: InfrastructureAsset | null
  assetType?: string | null
  onAnalysisUpdated?: (updated: AnalysisRun) => void
}

export const getSeverityBadgeClass = (level?: string | null) => {
  switch (level?.toLowerCase()) {
    case 'none':
      return 'bg-slate-100 text-slate-700 border-slate-300'
    case 'minor':
      return 'bg-emerald-100 text-emerald-800 border-emerald-300'
    case 'moderate':
      return 'bg-amber-100 text-amber-800 border-amber-300'
    case 'severe':
      return 'bg-orange-100 text-orange-800 border-orange-300'
    case 'critical':
      return 'bg-rose-100 text-rose-800 border-rose-300'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-300'
  }
}

export const AnalysisModal: React.FC<AnalysisModalProps> = ({
  isOpen,
  onClose,
  image,
  analysis,
  asset,
  assetType,
  onAnalysisUpdated: _onAnalysisUpdated,
}) => {
  const { role } = useAuth()
  
  // 5 switchable panes: original, detections, mask, xai, severity
  type ActivePane = 'original' | 'detections' | 'mask' | 'xai' | 'severity'
  const [activePane, setActivePane] = useState<ActivePane>('detections')

  const [showMask, setShowMask] = useState(true)
  const [maskOpacity, setMaskOpacity] = useState(0.6)
  const [maskUrl, setMaskUrl] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [_loadingMask, setLoadingMask] = useState(false)

  // Detector filter and asset metadata for domain check
  const [detectorFilter, setDetectorFilter] = useState<string>('all')
  const [assetInfo, setAssetInfo] = useState<{ asset_type?: string; material_type?: string; name?: string } | null>(
    asset ? { asset_type: asset.asset_type, material_type: asset.material_type, name: asset.name } : null
  )

  // Explainable AI (XAI) state
  const [explanations, setExplanations] = useState<ExplanationItem[]>([])
  const [, setLoadingExplanations] = useState(false)
  const [generatingExplanations, setGeneratingExplanations] = useState(false)
  const [xaiMsg, setXaiMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [selectedExpId, setSelectedExpId] = useState<number | null>(null)
  const [xaiOpacity, setXaiOpacity] = useState<number>(0.65)
  const [overlayBlobUrls, setOverlayBlobUrls] = useState<Record<number, string>>({})

  // Side-by-side comparison state
  const [compareMode, setCompareMode] = useState<boolean>(false)
  const [compareExpA, setCompareExpA] = useState<number | null>(null)
  const [compareExpB, setCompareExpB] = useState<number | null>(null)
  const [compareResult, setCompareResult] = useState<CompareMapsResult | null>(null)
  const [comparingMaps, setComparingMaps] = useState<boolean>(false)

  const pollingRef = useRef<number | null>(null)

  useEffect(() => {
    if (asset) {
      setAssetInfo({ asset_type: asset.asset_type, material_type: asset.material_type, name: asset.name })
      return
    }
    if (assetType) {
      setAssetInfo({ asset_type: assetType })
      return
    }
    if (!isOpen || !image.inspection_id) return

    let active = true
    const loadAsset = async () => {
      try {
        const insp = await inspectionsApi.getById(image.inspection_id)
        if (insp?.asset_id) {
          const a = await assetsApi.getById(insp.asset_id)
          if (active && a) {
            setAssetInfo({ asset_type: a.asset_type, material_type: a.material_type, name: a.name })
          }
        }
      } catch (err) {
        console.warn('Could not load asset info for domain check', err)
      }
    }
    loadAsset()
    return () => { active = false }
  }, [isOpen, image.inspection_id, asset, assetType])

  const availableDetectors = useMemo(() => {
    const set = new Set<string>()
    analysis.detections?.forEach((d) => {
      if (d.model_id) set.add(d.model_id)
    })
    analysis.models_used?.forEach((m) => {
      if (m !== 'unetplusplus_crack500') set.add(m)
    })
    return Array.from(set)
  }, [analysis])

  const filteredDetections = useMemo(() => {
    if (detectorFilter === 'all') return analysis.detections || []
    return (analysis.detections || []).filter((d) => d.model_id === detectorFilter)
  }, [analysis.detections, detectorFilter])

  const domainWarnings = useMemo(() => {
    const warnings: string[] = []
    if (!assetInfo?.asset_type) return warnings
    const normAsset = assetInfo.asset_type.trim().toLowerCase()
    const models = analysis.models_used || []

    if (models.includes('yolov8s_rdd2022') && normAsset !== 'road') {
      warnings.push(
        `Road damage detector (yolov8s_rdd2022) applied to non-road asset ("${assetInfo.name || normAsset}"). Trained on road damage images (RDD2022); cross-domain predictions are not validated for bridge/concrete structures.`
      )
    }

    if (models.includes('A2_rtdetr_l') && normAsset === 'road') {
      warnings.push(
        `CODEBRIM defect detector (A2_rtdetr_l) applied to road pavement asset ("${assetInfo.name || normAsset}"). Trained on bridge defect images (CODEBRIM); not validated for asphalt/pavement surfaces.`
      )
    }

    return warnings
  }, [assetInfo, analysis.models_used])

  // Severity assessment state
  const [severity, setSeverity] = useState<SeverityAssessment | null>(null)
  const [loadingSeverity, setLoadingSeverity] = useState(false)
  const [severityMsg, setSeverityMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCorrectForm, setShowCorrectForm] = useState(false)
  const [correctSeverity, setCorrectSeverity] = useState<string>('moderate')
  const [reviewComment, setReviewComment] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)

  const loadSeverity = async () => {
    try {
      setLoadingSeverity(true)
      const data = await severityApi.getImageSeverity(image.image_id)
      setSeverity(data)
      if (data) {
        setCorrectSeverity(data.final_severity || data.severity_level)
      }
    } catch {
      setSeverity(null)
    } finally {
      setLoadingSeverity(false)
    }
  }

  const handleConfirmSeverity = async () => {
    if (!severity) return
    try {
      setSubmittingReview(true)
      setSeverityMsg(null)
      const updated = await severityApi.review(severity.assessment_id, {
        action: 'confirm',
        comment: reviewComment.trim() || 'Severity confirmed by civil engineer',
      })
      setSeverity(updated)
      setSeverityMsg({ type: 'success', text: 'Advisory severity successfully confirmed!' })
      setReviewComment('')
    } catch (err: any) {
      setSeverityMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to confirm severity.' })
    } finally {
      setSubmittingReview(false)
    }
  }

  const handleCorrectSeverity = async () => {
    if (!severity) return
    if (!reviewComment.trim()) {
      setSeverityMsg({ type: 'error', text: 'A non-empty review comment is required when correcting severity.' })
      return
    }
    try {
      setSubmittingReview(true)
      setSeverityMsg(null)
      const updated = await severityApi.review(severity.assessment_id, {
        action: 'correct',
        final_severity: correctSeverity,
        comment: reviewComment.trim(),
      })
      setSeverity(updated)
      setSeverityMsg({ type: 'success', text: `Severity corrected to ${correctSeverity.toUpperCase()}!` })
      setShowCorrectForm(false)
      setReviewComment('')
    } catch (err: any) {
      setSeverityMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to correct severity.' })
    } finally {
      setSubmittingReview(false)
    }
  }

  const handleRecomputeSeverity = async () => {
    try {
      setSubmittingReview(true)
      setSeverityMsg(null)
      const updated = await severityApi.recompute(image.image_id)
      setSeverity(updated)
      setSeverityMsg({ type: 'success', text: 'Severity recomputed with current active rules!' })
    } catch (err: any) {
      setSeverityMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to recompute severity.' })
    } finally {
      setSubmittingReview(false)
    }
  }

  const loadExplanations = async (silent = false) => {
    try {
      if (!silent) setLoadingExplanations(true)
      const data = await explainApi.getImageExplanations(image.image_id)
      setExplanations(data)

      if (data.length > 0 && !selectedExpId) {
        const completed = data.find((e) => e.status === 'done')
        if (completed) setSelectedExpId(completed.explanation_id)
        else setSelectedExpId(data[0].explanation_id)
      }

      const hasPending = data.some((e) => e.status === 'pending' || e.status === 'in_progress')
      if (hasPending) {
        if (pollingRef.current) window.clearTimeout(pollingRef.current)
        pollingRef.current = window.setTimeout(() => loadExplanations(true), 2500)
      } else {
        setGeneratingExplanations(false)
      }
    } catch (err: any) {
      console.warn('Could not load explanations', err)
      setGeneratingExplanations(false)
    } finally {
      if (!silent) setLoadingExplanations(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      loadSeverity()
      loadExplanations()
    }
    return () => {
      if (pollingRef.current) {
        window.clearTimeout(pollingRef.current)
      }
    }
  }, [isOpen, image.image_id])

  // Fetch overlay blobs for completed explanations
  useEffect(() => {
    let active = true
    const fetchBlobs = async () => {
      for (const exp of explanations) {
        if (exp.status === 'done' && exp.overlay_path && !overlayBlobUrls[exp.explanation_id]) {
          try {
            const url = await explainApi.getOverlayBlobUrl(exp.explanation_id)
            if (active) {
              setOverlayBlobUrls((prev) => ({ ...prev, [exp.explanation_id]: url }))
            } else {
              URL.revokeObjectURL(url)
            }
          } catch (e) {
            console.error(`Failed to fetch overlay blob for explanation #${exp.explanation_id}`, e)
          }
        }
      }
    }
    if (explanations.length > 0) {
      fetchBlobs()
    }
    return () => {
      active = false
    }
  }, [explanations])

  useEffect(() => {
    return () => {
      Object.values(overlayBlobUrls).forEach((u) => URL.revokeObjectURL(u))
    }
  }, [])

  const handleTriggerExplain = async () => {
    try {
      setGeneratingExplanations(true)
      setXaiMsg(null)
      const created = await explainApi.triggerExplain(image.image_id)
      setExplanations(created)
      if (created.length > 0) {
        setSelectedExpId(created[0].explanation_id)
      }
      setActivePane('xai')
      setXaiMsg({ type: 'success', text: `Triggered attention map generation for ${created.length} model/method targets.` })

      if (pollingRef.current) window.clearTimeout(pollingRef.current)
      pollingRef.current = window.setTimeout(() => loadExplanations(true), 2500)
    } catch (err: any) {
      setXaiMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to trigger attention map generation.' })
      setGeneratingExplanations(false)
    }
  }

  const handleRunComparison = async () => {
    if (!compareExpA || !compareExpB) {
      setXaiMsg({ type: 'error', text: 'Please select both Map A and Map B to compare.' })
      return
    }
    if (compareExpA === compareExpB) {
      setXaiMsg({ type: 'error', text: 'Please select two different explanation maps for comparison.' })
      return
    }
    try {
      setComparingMaps(true)
      setXaiMsg(null)
      const res = await explainApi.compareMaps(compareExpA, compareExpB)
      setCompareResult(res)
    } catch (err: any) {
      setXaiMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to compare attention maps.' })
    } finally {
      setComparingMaps(false)
    }
  }

  const handleDownloadCurrentOverlay = async (exp: ExplanationItem) => {
    try {
      const fn = `${image.original_filename.replace(/\.[^/.]+$/, '')}_${exp.model_id}_${exp.method}_overlay.png`
      await explainApi.downloadOverlay(exp.explanation_id, fn)
    } catch (err: any) {
      setXaiMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to download overlay.' })
    }
  }

  // Fetch image blob
  useEffect(() => {
    let active = true
    let imgBlobUrl: string | null = null

    const fetchImg = async () => {
      try {
        const url = await imagesApi.getFileBlobUrl(image.image_id)
        if (active) {
          imgBlobUrl = url
          setImageUrl(url)
        } else {
          URL.revokeObjectURL(url)
        }
      } catch (e) {
        console.error('Failed to load image blob', e)
      }
    }

    if (isOpen) {
      fetchImg()
    }

    return () => {
      active = false
      if (imgBlobUrl) {
        URL.revokeObjectURL(imgBlobUrl)
      }
    }
  }, [isOpen, image.image_id])

  // Fetch mask blob if segmentation crack mask is available
  useEffect(() => {
    let active = true
    let maskBlobUrl: string | null = null

    const fetchMask = async () => {
      if (!analysis.crack_measurement?.mask_path) return
      try {
        setLoadingMask(true)
        const url = await analysisApi.getMaskBlobUrl(analysis.run_id)
        if (active) {
          maskBlobUrl = url
          setMaskUrl(url)
        } else {
          URL.revokeObjectURL(url)
        }
      } catch (err) {
        console.warn('Mask not available or failed to load', err)
      } finally {
        if (active) setLoadingMask(false)
      }
    }

    if (isOpen) {
      fetchMask()
    }

    return () => {
      active = false
      if (maskBlobUrl) {
        URL.revokeObjectURL(maskBlobUrl)
      }
    }
  }, [isOpen, analysis.run_id, analysis.crack_measurement?.mask_path])

  if (!isOpen) return null

  const m = analysis.crack_measurement

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Run #{analysis.run_id} &bull; Image #{image.image_id}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  analysis.status === 'done'
                    ? 'bg-emerald-100 text-emerald-800'
                    : analysis.status === 'failed'
                    ? 'bg-rose-100 text-rose-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {analysis.status}
              </span>
              {analysis.seconds !== null && analysis.seconds !== undefined && (
                <span className="text-[11px] text-slate-500 font-mono">
                  ({analysis.seconds.toFixed(2)}s)
                </span>
              )}
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              {image.original_filename}
            </h2>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-2 rounded-lg hover:bg-slate-200 transition-colors text-xl font-bold"
            title="Close"
          >
            &times;
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          
          {/* Permanent Mandatory Engineering & Attention Maps Disclaimer */}
          <div className="bg-amber-50 border-l-4 border-amber-500 p-3.5 rounded-r-xl shadow-xs">
            <div className="flex items-start space-x-3">
              <span className="text-xl leading-none shrink-0">⚠️</span>
              <div className="text-xs text-amber-900 leading-relaxed">
                <p className="font-bold text-amber-950 uppercase tracking-wider text-[11px] mb-0.5">
                  Advisory Engineering &amp; Attention Maps Disclaimer
                </p>
                <p className="font-medium">
                  Attention maps show which image regions influenced the model's output. They do not prove that a defect is present or that the model is correct. AI result for engineer review, not a final structural safety verdict.
                </p>
              </div>
            </div>
          </div>

          {/* Scale note if any */}
          {analysis.image_scale_note && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
              <span className="font-semibold">Resolution Note: </span>
              {analysis.image_scale_note}
            </div>
          )}

          {/* XAI Notifications */}
          {xaiMsg && (
            <div
              className={`p-3 rounded-lg text-xs font-medium flex items-center justify-between ${
                xaiMsg.type === 'success'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              <span>{xaiMsg.text}</span>
              <button
                onClick={() => setXaiMsg(null)}
                className="text-slate-400 hover:text-slate-600 font-bold ml-2 text-sm"
              >
                &times;
              </button>
            </div>
          )}

          {/* Visualization Panel: Five Switchable Panes Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 p-2.5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                onClick={() => setActivePane('original')}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                  activePane === 'original'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                📷 1. Original
              </button>
              <button
                onClick={() => setActivePane('detections')}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                  activePane === 'detections'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                🎯 2. Detections ({analysis.detections?.length || 0})
              </button>
              <button
                onClick={() => setActivePane('mask')}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                  activePane === 'mask'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                🔍 3. Segmentation Mask
              </button>
              <button
                onClick={() => setActivePane('xai')}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                  activePane === 'xai'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                🔥 4. AI Attention Map {explanations.length > 0 && `(${explanations.length})`}
              </button>
              <button
                onClick={() => setActivePane('severity')}
                className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
                  activePane === 'severity'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                ⚠️ 5. Damage Assessment
              </button>
            </div>

            {/* Explain Action Button */}
            <button
              onClick={handleTriggerExplain}
              disabled={generatingExplanations}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors disabled:opacity-50"
              title="Generate Explainable AI attention maps for models used in this analysis"
            >
              {generatingExplanations ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span>Computing Attention...</span>
                </>
              ) : (
                <>
                  <span>⚡ Explain (XAI)</span>
                </>
              )}
            </button>
          </div>

          {/* ========================================================================= */}
          {/* PANE 1: ORIGINAL IMAGE                                                   */}
          {/* ========================================================================= */}
          {activePane === 'original' && (
            <div className="space-y-4">
              <div className="relative w-full bg-slate-950 rounded-xl overflow-hidden shadow-inner flex items-center justify-center p-2 min-h-[380px]">
                {imageUrl ? (
                  <div
                    className="relative max-w-full max-h-[550px] inline-block"
                    style={{ aspectRatio: `${image.width_px} / ${image.height_px}` }}
                  >
                    <img
                      src={imageUrl}
                      alt={image.original_filename}
                      className="w-full h-full object-contain block"
                    />
                  </div>
                ) : (
                  <div className="text-slate-400 text-xs animate-pulse">Loading original photo...</div>
                )}
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs flex flex-wrap gap-4 text-slate-600">
                <span><strong>Filename:</strong> {image.original_filename}</span>
                <span><strong>Resolution:</strong> {image.width_px} &times; {image.height_px} px</span>
                <span><strong>Source:</strong> {image.source}</span>
                <span><strong>Quality:</strong> {image.quality_status}</span>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* PANE 2: DETECTIONS (BOXES)                                               */}
          {/* ========================================================================= */}
          {activePane === 'detections' && (
            <div className="space-y-6">
              {/* Domain Warning Banner if cross-domain inference detected */}
              {domainWarnings.length > 0 && (
                <div className="bg-orange-50 border-l-4 border-orange-500 p-4 rounded-r-xl shadow-xs space-y-1.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">⚠️</span>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-orange-950">
                      Model Domain Applicability Warning
                    </h4>
                  </div>
                  {domainWarnings.map((warn, i) => (
                    <p key={i} className="text-xs text-orange-900 pl-6 leading-relaxed">
                      {warn}
                    </p>
                  ))}
                </div>
              )}

              {/* Color-Coded Defect Legend */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">
                    Defect Class Color Legend
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium">
                    Road (RDD2022) &amp; Bridge (CODEBRIM) Taxonomies
                  </span>
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                  {Object.entries(DEFECT_COLORS).map(([key, item]) => (
                    <div key={key} className="flex items-center space-x-1.5 p-1.5 rounded-lg bg-white border border-slate-200 shadow-2xs">
                      <span
                        className="w-3 h-3 rounded-full shrink-0 shadow-xs"
                        style={{ backgroundColor: item.stroke }}
                      />
                      <div className="truncate">
                        <span className="text-[11px] text-slate-800 font-semibold block truncate">
                          {item.name}
                        </span>
                        <span className="text-[9px] text-slate-400 block truncate">
                          {item.category}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Controls Bar for Detector Filtering */}
              <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-100 p-3 rounded-xl border border-slate-200 text-xs">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-slate-700">Filter Detector:</span>
                  <div className="inline-flex rounded-lg border border-slate-300 p-0.5 bg-white shadow-2xs">
                    <button
                      onClick={() => setDetectorFilter('all')}
                      className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                        detectorFilter === 'all'
                          ? 'bg-indigo-600 text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      All ({analysis.detections?.length || 0})
                    </button>
                    {availableDetectors.map((det) => {
                      const count = (analysis.detections || []).filter((d) => d.model_id === det).length
                      const label = det === 'A2_rtdetr_l' ? 'CODEBRIM (RT-DETR-L)' : det === 'yolov8s_rdd2022' ? 'Road (YOLOv8s)' : det
                      return (
                        <button
                          key={det}
                          onClick={() => setDetectorFilter(det)}
                          className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                            detectorFilter === det
                              ? 'bg-indigo-600 text-white shadow-xs'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          {label} ({count})
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div className="text-[11px] text-slate-600">
                  Showing <strong>{filteredDetections.length}</strong> of {analysis.detections?.length || 0} detections
                </div>
              </div>

              {/* Visual Display with Bounding Boxes */}
              <div className="relative w-full bg-slate-950 rounded-xl overflow-hidden shadow-inner flex items-center justify-center p-2 min-h-[360px]">
                {imageUrl ? (
                  <div
                    className="relative max-w-full max-h-[550px] inline-block"
                    style={{ aspectRatio: `${image.width_px} / ${image.height_px}` }}
                  >
                    <img
                      src={imageUrl}
                      alt={image.original_filename}
                      className="w-full h-full object-contain block"
                    />

                    {/* Bounding Boxes SVG Overlay */}
                    {filteredDetections.length > 0 && (
                      <svg
                        viewBox={`0 0 ${image.width_px} ${image.height_px}`}
                        className="absolute inset-0 w-full h-full pointer-events-none"
                      >
                        {filteredDetections.map((box, idx) => {
                          const bw = box.x_max - box.x_min
                          const bh = box.y_max - box.y_min
                          const color = getDefectColor(box.damage_type, box.damage_label)
                          const detBadge = box.model_id === 'A2_rtdetr_l' ? 'CODEBRIM' : box.model_id === 'yolov8s_rdd2022' ? 'RDD' : box.model_id
                          const label = `[${detBadge}] ${box.damage_label || box.damage_type} ${(box.confidence * 100).toFixed(0)}%`

                          return (
                            <g key={box.detection_id || idx}>
                              <rect
                                x={box.x_min}
                                y={box.y_min}
                                width={bw}
                                height={bh}
                                fill={color.fill}
                                stroke={color.stroke}
                                strokeWidth="3"
                              />
                              <rect
                                x={box.x_min}
                                y={Math.max(box.y_min - 22, 0)}
                                width={label.length * 7.5 + 12}
                                height="20"
                                fill={color.bg}
                                rx="3"
                              />
                              <text
                                x={box.x_min + 5}
                                y={Math.max(box.y_min - 7, 14)}
                                fill={color.text}
                                fontSize="11"
                                fontFamily="monospace"
                                fontWeight="bold"
                              >
                                {label}
                              </text>
                            </g>
                          )
                        })}
                      </svg>
                    )}
                  </div>
                ) : (
                  <div className="text-slate-400 text-xs animate-pulse">Loading visual layers...</div>
                )}
              </div>

              {/* Detections List */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center justify-between">
                  <span>Damage Detections ({filteredDetections.length})</span>
                  <span className="text-[11px] font-normal text-slate-500 font-mono">
                    {detectorFilter === 'all' ? 'All Active Detectors' : detectorFilter}
                  </span>
                </h3>

                {filteredDetections.length === 0 ? (
                  <p className="text-xs text-slate-500 italic py-3 text-center">
                    No discrete surface damage instances found for current filter.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {filteredDetections.map((det) => {
                      const color = getDefectColor(det.damage_type, det.damage_label)
                      const isCodebrim = det.model_id === 'A2_rtdetr_l'
                      return (
                        <div
                          key={det.detection_id}
                          className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-2xs flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center space-x-2.5">
                            <span
                              className="w-3 h-3 rounded-full shrink-0 shadow-2xs"
                              style={{ backgroundColor: color.stroke }}
                              title={color.name}
                            />
                            <div>
                              <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                                <span className="font-semibold text-slate-800">
                                  {det.damage_label} ({det.damage_type})
                                </span>
                                <span
                                  className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-medium ${
                                    isCodebrim
                                      ? 'bg-purple-100 text-purple-800 border border-purple-200'
                                      : 'bg-blue-100 text-blue-800 border border-blue-200'
                                  }`}
                                >
                                  {isCodebrim ? 'CODEBRIM' : det.model_id === 'yolov8s_rdd2022' ? 'RDD2022' : det.model_id}
                                </span>
                              </div>
                              <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                                Bounding box: [{det.x_min.toFixed(0)}, {det.y_min.toFixed(0)}, {det.x_max.toFixed(0)}, {det.y_max.toFixed(0)}] px
                              </div>
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-indigo-50 text-indigo-700 font-mono">
                              {(det.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* PANE 3: SEGMENTATION MASK                                                */}
          {/* ========================================================================= */}
          {activePane === 'mask' && (
            <div className="space-y-6">
              {/* Opacity Control Bar */}
              <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-100 p-3 rounded-xl border border-slate-200 text-xs">
                <div className="flex items-center space-x-3">
                  <span className="font-semibold text-slate-700">Mask Visibility:</span>
                  <label className="flex items-center space-x-2 cursor-pointer font-medium text-slate-800">
                    <input
                      type="checkbox"
                      checked={showMask}
                      onChange={(e) => setShowMask(e.target.checked)}
                      className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                    />
                    <span>Show Overlay</span>
                  </label>
                  {showMask && (
                    <div className="flex items-center space-x-2 pl-4 border-l border-slate-300">
                      <span className="text-slate-500">Opacity:</span>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.05"
                        value={maskOpacity}
                        onChange={(e) => setMaskOpacity(parseFloat(e.target.value))}
                        className="w-24 accent-indigo-600"
                      />
                      <span className="font-mono text-[11px] text-slate-600 font-bold">
                        {(maskOpacity * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
                <div className="text-slate-500 text-[11px]">
                  Model: <strong>U-Net++ (ResNet-34)</strong> &bull; CRACK500 Trained
                </div>
              </div>

              {/* Mask Visual Display */}
              <div className="relative w-full bg-slate-950 rounded-xl overflow-hidden shadow-inner flex items-center justify-center p-2 min-h-[360px]">
                {imageUrl ? (
                  <div
                    className="relative max-w-full max-h-[550px] inline-block"
                    style={{ aspectRatio: `${image.width_px} / ${image.height_px}` }}
                  >
                    <img
                      src={imageUrl}
                      alt={image.original_filename}
                      className="w-full h-full object-contain block"
                    />
                    {maskUrl && showMask && (
                      <img
                        src={maskUrl}
                        alt="Crack segmentation mask"
                        className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                        style={{
                          opacity: maskOpacity,
                          filter: 'drop-shadow(0 0 4px #ef4444)',
                        }}
                      />
                    )}
                  </div>
                ) : (
                  <div className="text-slate-400 text-xs animate-pulse">Loading segmentation mask...</div>
                )}
              </div>

              {/* Crack Geometry Metrics Table */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center justify-between">
                  <span>Crack Geometry Metrics</span>
                  <span className="text-[11px] font-normal text-slate-500 font-mono">
                    Model: U-Net++ ResNet34
                  </span>
                </h3>

                {!m ? (
                  <p className="text-xs text-slate-500 italic py-3 text-center">
                    No crack segmentation measurements recorded for this run.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-400 font-medium">
                          <th className="py-1.5 font-medium">Metric</th>
                          <th className="py-1.5 font-medium text-right">Value (Pixels)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Crack Length</td>
                          <td className="py-1.5 font-mono font-semibold text-right text-indigo-700">
                            {m.length_px.toFixed(1)} pixels
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Average Width</td>
                          <td className="py-1.5 font-mono font-semibold text-right text-indigo-700">
                            {m.avg_width_px.toFixed(2)} pixels
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Maximum Width</td>
                          <td className="py-1.5 font-mono font-semibold text-right text-indigo-700">
                            {m.max_width_px.toFixed(2)} pixels
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">P95 Width</td>
                          <td className="py-1.5 font-mono font-semibold text-right text-indigo-700">
                            {m.p95_width_px.toFixed(2)} pixels
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Crack Area</td>
                          <td className="py-1.5 font-mono text-right">
                            {m.area_px.toLocaleString()} pixels
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Surface Density</td>
                          <td className="py-1.5 font-mono text-right">
                            {m.density_percent.toFixed(2)}%
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Dominant Orientation</td>
                          <td className="py-1.5 font-mono text-right">
                            {m.orientation_deg.toFixed(1)}°
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Branch Points</td>
                          <td className="py-1.5 font-mono text-right">
                            {m.num_branch_points}
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">End Points</td>
                          <td className="py-1.5 font-mono text-right">
                            {m.num_end_points}
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Connected Components</td>
                          <td className="py-1.5 font-mono text-right">
                            {m.num_components}
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 font-medium text-slate-600">Measurement Mode</td>
                          <td className="py-1.5 font-mono text-right text-slate-500">
                            {m.width_mode} (2x Euclidean Distance Transform)
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* PANE 4: AI ATTENTION MAP (XAI)                                           */}
          {/* ========================================================================= */}
          {activePane === 'xai' && (
            <div className="space-y-6">
              {/* Explain Header / Control Toolbar */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    {/* Model & Method Selection */}
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                        Select Explanation Map
                      </label>
                      {explanations.length === 0 ? (
                        <span className="text-xs text-slate-400 italic">No explanations generated yet. Click "Explain (XAI)" above.</span>
                      ) : (
                        <select
                          value={selectedExpId || ''}
                          onChange={(e) => setSelectedExpId(Number(e.target.value))}
                          className="bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-2xs focus:ring-indigo-500"
                        >
                          {explanations.map((exp) => (
                            <option key={exp.explanation_id} value={exp.explanation_id}>
                              {exp.model_id === 'unetplusplus_crack500' ? 'U-Net++ Crack500' : exp.model_id} &bull; {exp.method.toUpperCase()} ({exp.status})
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* Opacity Slider */}
                    {!compareMode && (
                      <div className="pl-3 border-l border-slate-200">
                        <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                          Heatmap Opacity: {(xaiOpacity * 100).toFixed(0)}%
                        </label>
                        <input
                          type="range"
                          min="0.0"
                          max="1.0"
                          step="0.05"
                          value={xaiOpacity}
                          onChange={(e) => setXaiOpacity(parseFloat(e.target.value))}
                          className="w-28 accent-indigo-600"
                        />
                      </div>
                    )}
                  </div>

                  {/* Right Action Controls: Comparison Toggle & Download */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setCompareMode(!compareMode)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                        compareMode
                          ? 'bg-purple-600 text-white border-purple-600 shadow-xs'
                          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100 shadow-2xs'
                      }`}
                    >
                      {compareMode ? 'Exit Comparison Mode' : '⇄ Side-by-Side Comparison'}
                    </button>

                    {selectedExpId && (
                      (() => {
                        const cur = explanations.find((e) => e.explanation_id === selectedExpId)
                        if (!cur || cur.status !== 'done') return null
                        return (
                          <button
                            onClick={() => handleDownloadCurrentOverlay(cur)}
                            className="px-3 py-1.5 bg-white hover:bg-slate-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-bold shadow-2xs transition-colors"
                          >
                            📥 Download Overlay
                          </button>
                        )
                      })()
                    )}
                  </div>
                </div>

                {/* Colour Legend Bar */}
                <div className="pt-2 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-3">
                    <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                      Colour Legend:
                    </span>
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[10px] font-mono text-slate-500">Low (0.0)</span>
                      <div className="h-3 w-36 rounded-full bg-gradient-to-r from-blue-600 via-green-500 via-yellow-400 to-red-600 shadow-2xs" />
                      <span className="text-[10px] font-mono text-slate-500">High (1.0)</span>
                    </div>
                  </div>
                  <span className="text-[11px] text-slate-500 italic">
                    warmer = more influence on this model output, scaled per image
                  </span>
                </div>
              </div>

              {/* Side-by-Side Comparison View */}
              {compareMode ? (
                <div className="space-y-4">
                  <div className="p-4 bg-purple-50 rounded-xl border border-purple-200 flex flex-wrap items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-4 text-xs">
                      <div>
                        <span className="font-bold text-purple-900 block mb-1">Map A:</span>
                        <select
                          value={compareExpA || ''}
                          onChange={(e) => setCompareExpA(Number(e.target.value))}
                          className="bg-white border border-purple-300 rounded px-2.5 py-1 text-xs font-semibold text-slate-800"
                        >
                          <option value="">Select Map A</option>
                          {explanations.filter((e) => e.status === 'done').map((e) => (
                            <option key={e.explanation_id} value={e.explanation_id}>
                              {e.model_id} &bull; {e.method.toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>

                      <span className="text-purple-400 font-bold self-end mb-1">VS</span>

                      <div>
                        <span className="font-bold text-purple-900 block mb-1">Map B:</span>
                        <select
                          value={compareExpB || ''}
                          onChange={(e) => setCompareExpB(Number(e.target.value))}
                          className="bg-white border border-purple-300 rounded px-2.5 py-1 text-xs font-semibold text-slate-800"
                        >
                          <option value="">Select Map B</option>
                          {explanations.filter((e) => e.status === 'done').map((e) => (
                            <option key={e.explanation_id} value={e.explanation_id}>
                              {e.model_id} &bull; {e.method.toUpperCase()}
                            </option>
                          ))}
                        </select>
                      </div>

                      <button
                        onClick={handleRunComparison}
                        disabled={comparingMaps || !compareExpA || !compareExpB}
                        className="self-end px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-bold transition-colors disabled:opacity-50"
                      >
                        {comparingMaps ? 'Computing...' : 'Run Correlation'}
                      </button>
                    </div>

                    {compareResult && (
                      <div className="flex items-center space-x-4 bg-white px-3 py-1.5 rounded-lg border border-purple-200 text-xs font-mono">
                        <span><strong>Spearman:</strong> {compareResult.spearman_correlation.toFixed(3)}</span>
                        <span>&bull;</span>
                        <span><strong>Top 10% Overlap:</strong> {(compareResult.top_10_overlap * 100).toFixed(1)}%</span>
                        <span>&bull;</span>
                        <span className="text-purple-700 font-semibold">{compareResult.interpretation}</span>
                      </div>
                    )}
                  </div>

                  {/* Side-by-Side Images Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Map A */}
                    <div className="bg-slate-950 p-2 rounded-xl flex flex-col items-center">
                      <span className="text-[11px] text-slate-300 font-mono mb-1 self-start pl-1">
                        Map A Overlay
                      </span>
                      {compareExpA && overlayBlobUrls[compareExpA] ? (
                        <img
                          src={overlayBlobUrls[compareExpA]}
                          alt="Map A"
                          className="max-h-[380px] w-full object-contain rounded"
                        />
                      ) : (
                        <div className="h-[280px] flex items-center justify-center text-slate-500 text-xs">
                          Select Map A above
                        </div>
                      )}
                    </div>

                    {/* Map B */}
                    <div className="bg-slate-950 p-2 rounded-xl flex flex-col items-center">
                      <span className="text-[11px] text-slate-300 font-mono mb-1 self-start pl-1">
                        Map B Overlay
                      </span>
                      {compareExpB && overlayBlobUrls[compareExpB] ? (
                        <img
                          src={overlayBlobUrls[compareExpB]}
                          alt="Map B"
                          className="max-h-[380px] w-full object-contain rounded"
                        />
                      ) : (
                        <div className="h-[280px] flex items-center justify-center text-slate-500 text-xs">
                          Select Map B above
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                /* Single Map Visual Display */
                <div className="relative w-full bg-slate-950 rounded-xl overflow-hidden shadow-inner flex items-center justify-center p-2 min-h-[380px]">
                  {imageUrl ? (
                    <div
                      className="relative max-w-full max-h-[550px] inline-block"
                      style={{ aspectRatio: `${image.width_px} / ${image.height_px}` }}
                    >
                      {/* Base Image */}
                      <img
                        src={imageUrl}
                        alt={image.original_filename}
                        className="w-full h-full object-contain block"
                      />

                      {/* Selected Explanation Overlay */}
                      {selectedExpId && overlayBlobUrls[selectedExpId] && (
                        <img
                          src={overlayBlobUrls[selectedExpId]}
                          alt="Attention map overlay"
                          className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                          style={{ opacity: xaiOpacity }}
                        />
                      )}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-xs animate-pulse">Loading visual layers...</div>
                  )}
                </div>
              )}

              {/* Metadata Details Card for Selected Explanation */}
              {selectedExpId && (
                (() => {
                  const cur = explanations.find((e) => e.explanation_id === selectedExpId)
                  if (!cur) return null
                  const p = cur.params || {}
                  return (
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                      <div className="flex items-center justify-between font-bold text-slate-800 border-b border-slate-200 pb-2">
                        <span>Explanation Details: {cur.model_id} &bull; {cur.method.toUpperCase()}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono ${
                          cur.status === 'done' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {cur.status} {cur.seconds ? `(${cur.seconds.toFixed(2)}s)` : ''}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-slate-600">
                        <div>
                          <strong>Target Layer:</strong> <span className="font-mono">{p.target_layer || 'N/A'}</span>
                        </div>
                        <div>
                          <strong>Target Output:</strong> <span className="font-mono">{p.target_description || cur.target}</span>
                        </div>
                        <div>
                          <strong>Scaled Per Image:</strong> <span className="font-mono">Yes (0.0 to 1.0)</span>
                        </div>
                        {p.min_before_normalisation !== undefined && p.max_before_normalisation !== undefined && (
                          <div>
                            <strong>Raw Pre-Norm Range:</strong> [{p.min_before_normalisation.toFixed(4)}, {p.max_before_normalisation.toFixed(4)}]
                          </div>
                        )}
                        {p.inference_size && (
                          <div>
                            <strong>Inference Resolution:</strong> {p.inference_size[0]} &times; {p.inference_size[1]} px
                          </div>
                        )}
                      </div>

                      {cur.warnings && cur.warnings.length > 0 && (
                        <div className="mt-2 p-2 bg-amber-50 rounded border border-amber-200 text-amber-800 text-[11px]">
                          <strong>Notice:</strong> {cur.warnings.join('; ')}
                        </div>
                      )}
                    </div>
                  )
                })()
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* PANE 5: DAMAGE ASSESSMENT                                                */}
          {/* ========================================================================= */}
          {activePane === 'severity' && (
            <div className="space-y-6">
              {loadingSeverity ? (
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center text-xs text-slate-400 animate-pulse">
                  Loading advisory damage severity...
                </div>
              ) : severity ? (
                <div className="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-4">
                  {/* Header with Severity Badge, Score, and Priority */}
                  <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-3">
                    <div className="flex items-center space-x-3">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border shadow-2xs ${getSeverityBadgeClass(
                          severity.final_severity || severity.severity_level,
                        )}`}
                      >
                        {severity.final_severity
                          ? `Final: ${severity.final_severity}`
                          : `Advisory: ${severity.severity_level}`}
                      </span>
                      <div>
                        <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
                          <span>Advisory Damage Severity Assessment</span>
                          {severity.review_status === 'pending' ? (
                            <span className="bg-amber-100 text-amber-800 text-[10px] px-2 py-0.5 rounded font-medium border border-amber-300">
                              Awaiting Engineer Review
                            </span>
                          ) : (
                            <span className="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded font-medium border border-emerald-300">
                              Reviewed ({severity.review_status})
                            </span>
                          )}
                        </h3>
                        <div className="text-xs text-slate-500 flex items-center space-x-3 mt-0.5">
                          <span>
                            Score: <strong>{severity.score.toFixed(1)} / 100</strong>
                          </span>
                          <span>•</span>
                          <span>
                            Suggested Priority:{' '}
                            <strong className="capitalize text-slate-700">
                              {severity.final_priority ||
                                severity.priority_suggestion.replace(/_/g, ' ')}
                            </strong>
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {(role === 'admin' || role === 'civil_engineer') && (
                        <button
                          onClick={handleRecomputeSeverity}
                          disabled={submittingReview}
                          className="px-3 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded text-xs font-medium shadow-2xs transition-colors"
                          title="Recompute severity using saved detection/geometry results and current rules"
                        >
                          🔄 Recompute (Current Rules)
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Status / Success Messages */}
                  {severityMsg && (
                    <div
                      className={`p-2.5 rounded-lg text-xs font-medium ${
                        severityMsg.type === 'success'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}
                    >
                      {severityMsg.text}
                    </div>
                  )}

                  {/* Mandatory Advisory Standard Labels */}
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs space-y-1">
                    <p className="font-semibold">
                      ⚠️ Advisory result for engineer review. Not a structural safety verdict. Critical means urgent engineering review.
                    </p>
                    <div className="text-[11px] text-amber-800 flex flex-wrap gap-x-4">
                      <span>
                        Rules Version: <code>{severity.rules_version}</code>
                      </span>
                      <span>
                        SHA-256: <code>{severity.rules_sha256.substring(0, 10)}...</code>
                      </span>
                      <span>
                        Status: <code>{severity.review_status}</code>
                      </span>
                    </div>
                  </div>

                  {/* Factor Points Breakdown Table */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                      Factor Breakdown &amp; Points Attribution
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-200 text-slate-400 font-medium">
                            <th className="py-1.5">Factor</th>
                            <th className="py-1.5">Measured Value</th>
                            <th className="py-1.5">Rule / Band</th>
                            <th className="py-1.5 text-right">Points</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700">
                          {(Array.isArray(severity.factors) ? severity.factors : (typeof severity.factors_json === 'string' ? JSON.parse(severity.factors_json || '[]') : (severity.factors_json || []))).map((f: any, idx: number) => (
                            <tr key={idx}>
                              <td className="py-1.5 font-medium text-slate-800">
                                {f.factor}
                              </td>
                              <td className="py-1.5 font-mono text-slate-600">
                                {f.value_str}
                              </td>
                              <td className="py-1.5 text-slate-500 text-[11px]">
                                {f.description}
                              </td>
                              <td className="py-1.5 font-mono font-bold text-right text-indigo-700">
                                +{f.points.toFixed(1)}
                              </td>
                            </tr>
                          ))}
                          <tr className="border-t-2 border-slate-300 font-bold bg-slate-100/50">
                            <td className="py-2" colSpan={3}>
                              Total Base Score (capped at 100)
                            </td>
                            <td className="py-2 font-mono text-right text-indigo-900">
                              {severity.score.toFixed(1)}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Civil Engineer Review Form */}
                  {(role === 'admin' || role === 'civil_engineer') ? (
                    <div className="pt-3 border-t border-slate-200 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                          Civil Engineer Review Actions
                        </span>
                        <div className="space-x-2">
                          <button
                            onClick={handleConfirmSeverity}
                            disabled={submittingReview}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold shadow-2xs transition-colors disabled:opacity-50"
                          >
                            ✓ Confirm Severity
                          </button>
                          <button
                            onClick={() => setShowCorrectForm(!showCorrectForm)}
                            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-semibold shadow-2xs transition-colors"
                          >
                            ✎ Correct Severity
                          </button>
                        </div>
                      </div>

                      {/* Correction Drawer */}
                      {showCorrectForm && (
                        <div className="p-3 bg-white rounded-lg border border-amber-200 space-y-3">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-slate-700 mb-1">
                                Corrected Severity Level:
                              </label>
                              <select
                                value={correctSeverity}
                                onChange={(e) => setCorrectSeverity(e.target.value)}
                                className="w-full text-xs p-1.5 border border-slate-300 rounded bg-white font-medium capitalize"
                              >
                                <option value="none">None</option>
                                <option value="minor">Minor</option>
                                <option value="moderate">Moderate</option>
                                <option value="severe">Severe</option>
                                <option value="critical">Critical</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-slate-700 mb-1">
                                Review Note / Justification <span className="text-rose-500">*</span>:
                              </label>
                              <input
                                type="text"
                                value={reviewComment}
                                onChange={(e) => setReviewComment(e.target.value)}
                                placeholder="Explain reason for overriding automated severity..."
                                className="w-full text-xs p-1.5 border border-slate-300 rounded"
                              />
                            </div>
                          </div>
                          <div className="flex justify-end space-x-2 pt-1">
                            <button
                              onClick={() => setShowCorrectForm(false)}
                              className="px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleCorrectSeverity}
                              disabled={submittingReview}
                              className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-semibold shadow-2xs"
                            >
                              Submit Correction
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Existing Review Record */}
                      {severity.reviewed_by && (
                        <div className="text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-200">
                          <strong>Review History:</strong> Reviewed by User #{severity.reviewed_by} at{' '}
                          {new Date(severity.reviewed_at!).toLocaleString()} (Status: {severity.review_status}).
                          {severity.review_comment && ` Note: "${severity.review_comment}"`}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-400 italic">
                      Note: Severity confirmation and corrections are restricted to Civil Engineers and Administrators.
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* Model information & Mandatory Validation Disclaimer */}
          <div className="p-3 bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-700 space-y-1">
            <div className="font-semibold text-slate-900">
              Models Deployed: YOLOv8s (Road Damage), RT-DETR-L (CODEBRIM Bridge Defects), U-Net++ ResNet-34 (Semantic Crack Segmentation), EDT2 (Crack Geometry), Grad-CAM / EigenCAM (Explainable AI)
            </div>
            <p className="italic text-slate-600">
              "Models were trained on benchmark datasets (RDD2022, Crack500, CODEBRIM). Results on other surfaces are not validated. AI result for engineer review, not a final structural safety verdict."
            </p>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
          >
            Close Analysis Viewer
          </button>
        </div>

      </div>
    </div>
  )
}
