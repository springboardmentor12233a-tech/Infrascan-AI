import { apiClient, extractApiError } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_IMAGES } from '@/data/mockData'
import type { InspectionImage, ImageQualityStatus, CalibrationStatus, AiProcessingStatus } from '@/types'

let imagesStore: InspectionImage[] = MOCK_IMAGES.map((img) => ({
  ...img,
  processingStatus: (img.hasAiAnalysis ? 'Completed' : 'Not Started') as AiProcessingStatus,
  qualityStatus: 'Good Quality' as ImageQualityStatus,
  calibrationStatus: (img.calibrated ? 'Calibration Verified' : 'Not Calibrated') as CalibrationStatus,
  category: 'Crack Evidence',
  captureMethod: 'UAV',
  tags: ['concrete', 'surface'],
}))

/** Build a full image file URL for backend-served images */
function imageFileUrl(id: string): string {
  return `${API_CONFIG.baseUrl}/images/${id}/file`
}

/** Map backend ImageRecord to frontend InspectionImage */
function mapApiImage(r: Record<string, unknown>): InspectionImage {
  const id = r.id as string
  return {
    id,
    filename: r.original_filename as string,
    url: imageFileUrl(id),
    assetId: r.asset_id as string,
    assetName: 'Asset',
    inspectionId: r.inspection_id as string,
    uploadDate: r.created_at as string,
    resolution: r.image_width ? `${r.image_width} x ${r.image_height}` : '0 x 0',
    fileSizeBytes: r.file_size as number,
    cameraModel: 'Unknown',
    calibrated: false,
    calibrationStatus: 'Not Calibrated',
    hasAiAnalysis: false,
    processingStatus: 'Not Started',
    qualityStatus: (r.image_quality_status as ImageQualityStatus) || 'Requires Review',
    category: 'Uncategorized',
    captureMethod: 'Ground Survey',
    tags: [],
  }
}

export const imageService = {
  async getAll(): Promise<InspectionImage[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 180))
      return [...imagesStore]
    }
    try {
      const { data } = await apiClient.get('/images')
      return (data as Record<string, unknown>[]).map(mapApiImage)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async getById(id: string): Promise<InspectionImage | undefined> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 120))
      return imagesStore.find((img) => img.id === id)
    }
    try {
      const { data } = await apiClient.get(`/images/${id}`)
      return mapApiImage(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  /**
   * Upload images. In mock mode, accepts pre-built image metadata objects.
   * In live API mode, the caller should use `uploadFiles()` instead.
   */
  async uploadBulk(newImages: Omit<InspectionImage, 'id'>[]): Promise<InspectionImage[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 500))
      const created: InspectionImage[] = newImages.map((img, idx) => ({
        ...img,
        id: `IMG-${410 + imagesStore.length + idx}`,
      }))
      imagesStore = [...created, ...imagesStore]
      return created
    }
    // In live mode this path shouldn't be reached — use uploadFiles() instead
    return newImages.map((img, idx) => ({ ...img, id: `IMG-API-${idx}` }))
  },

  /**
   * Upload actual File objects via multipart form-data to POST /images/upload.
   * Used in live API mode.
   */
  async uploadFiles(
    files: File[],
    metadata: { assetId: string; inspectionId: string }
  ): Promise<InspectionImage[]> {
    try {
      const results: InspectionImage[] = []
      for (const file of files) {
        const form = new FormData()
        form.append('file', file)
        form.append('asset_id', metadata.assetId)
        form.append('inspection_id', metadata.inspectionId)
        const { data } = await apiClient.post('/images/upload', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        results.push(mapApiImage(data as Record<string, unknown>))
      }
      return results
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async update(id: string, patch: Partial<InspectionImage>): Promise<InspectionImage> {
    if (API_CONFIG.enableMockData) {
      imagesStore = imagesStore.map((img) => (img.id === id ? { ...img, ...patch } : img))
      return imagesStore.find((img) => img.id === id)!
    }
    try {
      const { data } = await apiClient.patch(`/images/${id}`, patch)
      return mapApiImage(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async delete(id: string): Promise<void> {
    if (API_CONFIG.enableMockData) {
      imagesStore = imagesStore.filter((img) => img.id !== id)
      return
    }
    try {
      await apiClient.delete(`/images/${id}`)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  /** Returns the authenticated URL to serve an image file from the backend */
  getFileUrl(id: string): string {
    return imageFileUrl(id)
  },
}
