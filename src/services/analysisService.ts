import { apiClient, extractApiError } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_AI_ANALYSIS, MOCK_IMAGES, MOCK_ASSETS } from '@/data/mockData'
import type { AiAnalysisResult, AiProcessingStatus } from '@/types'

export interface AnalysisJobRecord {
  id: string
  imageId: string
  imageName: string
  assetId: string
  assetName: string
  inspectionId: string
  pipeline: string
  modelsUsed: string[]
  findingsCount: number
  status: AiProcessingStatus | 'Requires Review'
  createdAt: string
  durationMs: number
  reviewStatus: 'Pending Review' | 'Confirmed' | 'Rejected' | 'Corrected'
}

let jobsStore: AnalysisJobRecord[] = [
  {
    id: 'ANA-9001',
    imageId: MOCK_IMAGES[0].id,
    imageName: MOCK_IMAGES[0].filename,
    assetId: MOCK_ASSETS[0].id,
    assetName: MOCK_ASSETS[0].name,
    inspectionId: 'INSP-2026-089',
    pipeline: 'Complete Damage Analysis',
    modelsUsed: ['YOLO-Crack', 'U-Net-Seg', 'EfficientNet-Cls', 'Severity-Engine'],
    findingsCount: 2,
    status: 'Requires Review',
    createdAt: '2026-11-18T10:25:12Z',
    durationMs: 342,
    reviewStatus: 'Pending Review',
  },
  {
    id: 'ANA-9002',
    imageId: MOCK_IMAGES[1].id,
    imageName: MOCK_IMAGES[1].filename,
    assetId: MOCK_ASSETS[3].id,
    assetName: MOCK_ASSETS[3].name,
    inspectionId: 'INSP-2026-086',
    pipeline: 'Crack Analysis',
    modelsUsed: ['YOLO-Crack', 'U-Net-Seg'],
    findingsCount: 1,
    status: 'Completed',
    createdAt: '2026-11-10T14:15:00Z',
    durationMs: 289,
    reviewStatus: 'Confirmed',
  },
  {
    id: 'ANA-9003',
    imageId: MOCK_IMAGES[2].id,
    imageName: MOCK_IMAGES[2].filename,
    assetId: MOCK_ASSETS[1].id,
    assetName: MOCK_ASSETS[1].name,
    inspectionId: 'INSP-2026-087',
    pipeline: 'Surface Damage Analysis',
    modelsUsed: ['YOLO-Surface', 'SegFormer'],
    findingsCount: 0,
    status: 'Failed',
    createdAt: '2026-11-14T09:10:00Z',
    durationMs: 0,
    reviewStatus: 'Pending Review',
  },
]

/** Map backend AnalysisOut to AnalysisJobRecord */
function mapApiJob(r: Record<string, unknown>): AnalysisJobRecord {
  return {
    id: r.id as string,
    imageId: r.image_id as string,
    imageName: (r.image_name as string) || 'image.jpg',
    assetId: r.asset_id as string,
    assetName: (r.asset_name as string) || 'Asset',
    inspectionId: r.inspection_id as string,
    pipeline: r.pipeline_type as string,
    modelsUsed: (r.selected_models as string[]) || [],
    findingsCount: 0,
    status: r.job_status as AiProcessingStatus,
    createdAt: r.created_at as string,
    durationMs: 0,
    reviewStatus: 'Pending Review',
  }
}

export const analysisService = {
  async getJobs(): Promise<AnalysisJobRecord[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 180))
      return [...jobsStore]
    }
    try {
      const { data } = await apiClient.get('/analysis')
      return (data as Record<string, unknown>[]).map(mapApiJob)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async createJob(payload: {
    imageId: string
    imageName: string
    assetId: string
    assetName: string
    inspectionId: string
    pipeline: string
    modelsUsed: string[]
  }): Promise<AnalysisJobRecord> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 600))
      const created: AnalysisJobRecord = {
        id: `ANA-${9004 + jobsStore.length}`,
        ...payload,
        findingsCount: 1,
        status: 'Completed',
        createdAt: new Date().toISOString(),
        durationMs: 315,
        reviewStatus: 'Pending Review',
      }
      jobsStore = [created, ...jobsStore]
      return created
    }
    try {
      const apiPayload = {
        asset_id: payload.assetId,
        inspection_id: payload.inspectionId,
        image_id: payload.imageId,
        pipeline_type: payload.pipeline,
        selected_models: payload.modelsUsed,
      }
      const { data } = await apiClient.post('/analysis', apiPayload)
      return mapApiJob(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async getJobStatus(id: string): Promise<{ status: string; progress: number }> {
    if (API_CONFIG.enableMockData) {
      return { status: 'Completed', progress: 100 }
    }
    try {
      const { data } = await apiClient.get(`/analysis/${id}/status`)
      return { status: (data as Record<string, unknown>).job_status as string, progress: (data as Record<string, unknown>).progress_percentage as number }
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async retryJob(id: string): Promise<void> {
    if (API_CONFIG.enableMockData) {
      jobsStore = jobsStore.map((j) => (j.id === id ? { ...j, status: 'Completed', durationMs: 295 } : j))
      return
    }
    try {
      await apiClient.post(`/analysis/${id}/retry`)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async analyzeImage(imageId: string, imageName: string): Promise<AiAnalysisResult> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 800))
      if (MOCK_AI_ANALYSIS[imageId]) {
        return MOCK_AI_ANALYSIS[imageId]
      }
      return {
        id: `ANA-${Math.floor(1000 + Math.random() * 9000)}`,
        imageId,
        imageName,
        modelName: 'InfraScan-CrackNet-v2.4 (Demo)',
        modelVersion: '2.4.1-sim',
        inferenceTimeMs: 315,
        isDemoData: true,
        overallSeverity: 'High',
        confidenceMean: 0.92,
        calibrated: true,
        detections: [
          {
            id: 'DET-SIM-1',
            label: 'Transverse Crack',
            confidence: 0.94,
            x: 20,
            y: 35,
            width: 55,
            height: 22,
            severity: 'High',
            estimatedLengthMm: 980,
            estimatedWidthMm: 3.1,
            areaMm2: 3038,
          },
        ],
        segmentations: [
          {
            id: 'SEG-SIM-1',
            category: 'Transverse Crack',
            points: '200,250 420,235 610,260 740,248 740,268 610,280 420,255 200,270',
            color: '#F97316',
            opacity: 0.52,
          },
        ],
        summary:
          'Simulated AI inference detected transverse surface cracking. Connect FastAPI/PyTorch backend for live model predictions.',
        recommendations: [
          'Verify crack width with physical feeler gauge.',
          'Monitor for moisture ingress during next scheduled inspection.',
        ],
        analyzedAt: new Date().toISOString(),
      }
    }
    try {
      const { data } = await apiClient.post('/analysis/run', { imageId })
      return data as AiAnalysisResult
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },
}
