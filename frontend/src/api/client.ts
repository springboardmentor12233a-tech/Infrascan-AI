import axios from 'axios'

// API base URL
const defaultHost = (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1') ? '127.0.0.1' : 'localhost'
const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${defaultHost}:8000`

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
})

// Request interceptor to attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor to handle 401 Unauthorized errors with single silent refresh
let isRefreshing = false
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token!)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      // Avoid looping on authentication endpoints
      if (
        originalRequest.url?.includes('/auth/login') ||
        originalRequest.url?.includes('/auth/refresh')
      ) {
        return Promise.reject(error)
      }

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('role')
        localStorage.removeItem('user')

        const currentPath = window.location.pathname + window.location.search
        if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
        }
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshRes = await axios.post<TokenData>(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newAccessToken = refreshRes.data.access_token
        const newRefreshToken = refreshRes.data.refresh_token

        localStorage.setItem('token', newAccessToken)
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken)
        }

        apiClient.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`
        processQueue(null, newAccessToken)
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('role')
        localStorage.removeItem('user')

        const currentPath = window.location.pathname + window.location.search
        if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
        }
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  },
)

// Types
export interface User {
  user_id: number
  full_name: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

export interface TokenData {
  access_token: string
  refresh_token?: string
  token_type: string
  role: string
}

export interface UserSession {
  session_id: string
  user_agent: string | null
  ip: string | null
  created_at: string
  last_used_at: string
  expires_at: string
  is_current?: boolean
}

export interface AuditLogEntry {
  log_id: number
  user_id: number | null
  user_email?: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  ip_address: string | null
  created_at: string
}

export interface PaginatedUsers {
  items: User[]
  total: number
  page: number
  page_size: number
}

export interface PaginatedAuditLogs {
  items: AuditLogEntry[]
  total: number
  page: number
  page_size: number
}

export interface InfrastructureAsset {
  asset_id: number
  name: string
  asset_type: string
  material_type: string
  address: string | null
  latitude: number
  longitude: number
  construction_year: number
  responsible_department: string
  inspection_frequency_days: number
  importance_level: string
  created_by?: number | null
  created_at: string
  last_inspection_date?: string | null
}

export interface AssetListResponse {
  items: InfrastructureAsset[]
  total: number
  page: number
  page_size: number
}

export interface InspectionSummary {
  inspection_id: number
  inspector_id: number
  inspector_name: string | null
  inspection_date: string
  status: string
  created_at: string
}

export interface AssetDetail extends InfrastructureAsset {
  inspections: InspectionSummary[]
}

export interface Inspection {
  inspection_id: number
  asset_id: number
  asset_name: string | null
  inspector_id: number
  inspector_name: string | null
  inspection_date: string
  status: string
  created_at: string
}

export interface ImageMetadata {
  image_id: number
  inspection_id: number
  uploaded_by: number | null
  file_path: string
  original_filename: string
  file_hash: string
  width_px: number
  height_px: number
  file_size_bytes: number
  source: string
  blur_score: number
  brightness_score: number
  quality_status: 'passed' | 'warning' | 'rejected'
  quality_notes: string | null
  gps_latitude: number | null
  gps_longitude: number | null
  captured_at: string | null
  uploaded_at: string
  processed_file_path: string | null
  preprocess_status: 'not_run' | 'done' | 'failed'
  preprocess_steps: string | null
  preprocessed_at: string | null
}

export interface UploadResultItem {
  filename: string
  status: 'accepted' | 'warning' | 'rejected'
  message: string
  image?: ImageMetadata | null
}

export interface UploadBatchResponse {
  total_files: number
  accepted_count: number
  warning_count: number
  rejected_count: number
  results: UploadResultItem[]
}

export interface Detection {
  detection_id: number
  run_id: number
  model_id: string
  damage_type: string
  damage_label: string
  confidence: number
  x_min: number
  y_min: number
  x_max: number
  y_max: number
}

export interface CrackMeasurement {
  measurement_id: number
  run_id: number
  mask_path: string
  threshold: number
  crack_pixels: number
  length_px: number
  avg_width_px: number
  max_width_px: number
  p95_width_px: number
  area_px: number
  density_percent: number
  orientation_deg: number
  num_components: number
  num_branch_points: number
  num_end_points: number
  mm_per_pixel?: number | null
  length_mm?: number | null
  avg_width_mm?: number | null
  max_width_mm?: number | null
  width_mode: string
  scale_id?: number | null
  length_mm_uncertainty?: number | null
  width_mm_uncertainty?: number | null
  measurement_note?: string | null
}

export interface ImageScale {
  scale_id: number
  image_id: number
  method: 'manual_ratio' | 'reference_object'
  mm_per_pixel: number
  reference_mm?: number | null
  reference_px?: number | null
  point1_x?: number | null
  point1_y?: number | null
  point2_x?: number | null
  point2_y?: number | null
  camera_perpendicular: boolean
  uncertainty_percent: number
  is_current: boolean
  set_by?: number | null
  created_at: string
}

export interface SetScaleRequest {
  method?: 'manual_ratio' | 'reference_object'
  mm_per_pixel?: number
  reference_mm?: number
  point1_x?: number
  point1_y?: number
  point2_x?: number
  point2_y?: number
  point1?: [number, number]
  point2?: [number, number]
  camera_perpendicular: boolean
}

export interface AnalysisRun {
  run_id: number
  image_id: number
  status: 'pending' | 'in_progress' | 'done' | 'failed'
  error_message?: string | null
  started_at?: string | null
  finished_at?: string | null
  seconds?: number | null
  image_scale_note?: string | null
  models_used: string[]
  detections: Detection[]
  crack_measurement?: CrackMeasurement | null
}

export interface DetectorInfo {
  name: string
  model_id: string
  model_name: string
  model_class: string
  class_names: string[] | Record<string, string>
  conf: number
  imgsz: number
  applicable_asset_types: string[]
  domain_note: string
  validation_metrics?: Record<string, any> | null
}

export interface AnalyzeBatchResponse {
  total: number
  enqueued: number
  skipped: number
  runs: AnalysisRun[]
}

// API methods
export const authApi = {
  login: async (email: string, password: string): Promise<TokenData> => {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', password)

    const response = await apiClient.post<TokenData>('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
  },

  register: async (
    fullName: string,
    email: string,
    password: string,
  ): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', {
      full_name: fullName,
      email,
      password,
    })
    return response.data
  },

  refresh: async (refreshToken: string): Promise<TokenData> => {
    const response = await apiClient.post<TokenData>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  logout: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout')
    } finally {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('role')
      localStorage.removeItem('user')
    }
  },

  getSessions: async (): Promise<UserSession[]> => {
    const response = await apiClient.get<UserSession[]>('/auth/sessions')
    return response.data
  },

  revokeSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/auth/sessions/${sessionId}`)
  },

  forgotPassword: async (email: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/forgot-password', { email })
    return response.data
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password: newPassword,
    })
    return response.data
  },
}

export const usersApi = {
  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me')
    return response.data
  },

  updateMe: async (fullName: string): Promise<User> => {
    const response = await apiClient.put<User>('/users/me', {
      full_name: fullName,
    })
    return response.data
  },

  changePassword: async (
    oldPassword: string,
    newPassword: string,
  ): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(
      '/users/me/change-password',
      {
        old_password: oldPassword,
        new_password: newPassword,
      },
    )
    return response.data
  },

  getInspectors: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/users/inspectors')
    return response.data
  },

  getUsers: async (): Promise<User[]> => {
    const response = await apiClient.get<PaginatedUsers | User[]>('/users')
    if (Array.isArray(response.data)) {
      return response.data
    }
    return response.data.items
  },

  listUsers: async (params?: {
    search?: string
    role?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }): Promise<PaginatedUsers> => {
    const response = await apiClient.get<PaginatedUsers>('/users', { params })
    return response.data
  },

  createUser: async (data: {
    full_name: string
    email: string
    password: string
    role: string
  }): Promise<User> => {
    const response = await apiClient.post<User>('/users', data)
    return response.data
  },

  updateRole: async (userId: number, role: string): Promise<User> => {
    const response = await apiClient.put<User>(`/users/${userId}/role`, {
      role,
    })
    return response.data
  },

  updateActiveStatus: async (
    userId: number,
    isActive: boolean,
  ): Promise<User> => {
    const response = await apiClient.put<User>(`/users/${userId}/active`, {
      is_active: isActive,
    })
    return response.data
  },

  forceResetPassword: async (userId: number): Promise<{ message: string; reset_token: string }> => {
    const response = await apiClient.post<{ message: string; reset_token: string }>(
      `/users/${userId}/force-reset`,
    )
    return response.data
  },

  revokeUserSessions: async (userId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/users/${userId}/sessions`)
    return response.data
  },

  getUserAuditLogs: async (userId: number): Promise<AuditLogEntry[]> => {
    const response = await apiClient.get<AuditLogEntry[]>(`/users/${userId}/audit-logs`)
    return response.data
  },

  listAuditLogs: async (params?: {
    user_id?: number
    action?: string
    entity_type?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedAuditLogs> => {
    const response = await apiClient.get<PaginatedAuditLogs>('/audit-logs', { params })
    return response.data
  },

  exportAuditLogsUrl: (params?: { user_id?: number; action?: string; entity_type?: string }): string => {
    const searchParams = new URLSearchParams()
    if (params?.user_id) searchParams.append('user_id', String(params.user_id))
    if (params?.action) searchParams.append('action', params.action)
    if (params?.entity_type) searchParams.append('entity_type', params.entity_type)
    return `${API_BASE_URL}/audit-logs/export?${searchParams.toString()}`
  },
}

export const assetsApi = {
  list: async (params?: {
    search?: string
    asset_type?: string
    material_type?: string
    page?: number
    page_size?: number
  }): Promise<AssetListResponse> => {
    const response = await apiClient.get<AssetListResponse>('/assets', {
      params,
    })
    return response.data
  },

  getById: async (id: number): Promise<AssetDetail> => {
    const response = await apiClient.get<AssetDetail>(`/assets/${id}`)
    return response.data
  },

  create: async (
    data: Omit<
      InfrastructureAsset,
      'asset_id' | 'created_by' | 'created_at' | 'last_inspection_date'
    >,
  ): Promise<InfrastructureAsset> => {
    const response = await apiClient.post<InfrastructureAsset>('/assets', data)
    return response.data
  },

  update: async (
    id: number,
    data: Partial<InfrastructureAsset>,
  ): Promise<InfrastructureAsset> => {
    const response = await apiClient.put<InfrastructureAsset>(
      `/assets/${id}`,
      data,
    )
    return response.data
  },

  delete: async (id: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(
      `/assets/${id}`,
    )
    return response.data
  },

  getGeoJSON: async (): Promise<any> => {
    const response = await apiClient.get('/assets/geojson')
    return response.data
  },
}

export const inspectionsApi = {
  list: async (params?: {
    status?: string
    asset_id?: number
  }): Promise<Inspection[]> => {
    const response = await apiClient.get<Inspection[]>('/inspections', {
      params,
    })
    return response.data
  },

  getById: async (id: number): Promise<Inspection> => {
    const response = await apiClient.get<Inspection>(`/inspections/${id}`)
    return response.data
  },

  create: async (data: {
    asset_id: number
    inspector_id: number
    inspection_date: string
    status?: string
  }): Promise<Inspection> => {
    const response = await apiClient.post<Inspection>('/inspections', data)
    return response.data
  },

  updateStatus: async (
    id: number,
    status: string,
  ): Promise<Inspection> => {
    const response = await apiClient.put<Inspection>(
      `/inspections/${id}/status`,
      { status },
    )
    return response.data
  },
}

export const imagesApi = {
  upload: async (
    inspectionId: number,
    files: File[],
    source: string,
    onProgress?: (percent: number) => void,
  ): Promise<UploadBatchResponse> => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    formData.append('source', source)

    const response = await apiClient.post<UploadBatchResponse>(
      `/inspections/${inspectionId}/images`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percent = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            )
            onProgress(percent)
          }
        },
      },
    )
    return response.data
  },

  listByInspection: async (inspectionId: number): Promise<ImageMetadata[]> => {
    const response = await apiClient.get<ImageMetadata[]>(
      `/inspections/${inspectionId}/images`,
    )
    return response.data
  },

  getMetadata: async (imageId: number): Promise<ImageMetadata> => {
    const response = await apiClient.get<ImageMetadata>(`/images/${imageId}`)
    return response.data
  },

  getFileBlobUrl: async (imageId: number): Promise<string> => {
    const response = await apiClient.get(`/images/${imageId}/file`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  getProcessedFileBlobUrl: async (imageId: number): Promise<string> => {
    const response = await apiClient.get(`/images/${imageId}/processed`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  preprocessImage: async (imageId: number): Promise<ImageMetadata> => {
    const response = await apiClient.post<ImageMetadata>(
      `/images/${imageId}/preprocess`,
    )
    return response.data
  },

  preprocessInspection: async (
    inspectionId: number,
  ): Promise<ImageMetadata[]> => {
    const response = await apiClient.post<ImageMetadata[]>(
      `/inspections/${inspectionId}/preprocess`,
    )
    return response.data
  },

  delete: async (imageId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(
      `/images/${imageId}`,
    )
    return response.data
  },
}

export const analysisApi = {
  getModels: async (): Promise<DetectorInfo[]> => {
    const response = await apiClient.get<DetectorInfo[]>('/models')
    return response.data
  },

  analyzeImage: async (
    imageId: number,
    data?: { mm_per_pixel?: number; detectors?: string[] },
  ): Promise<AnalysisRun> => {
    const response = await apiClient.post<AnalysisRun>(
      `/images/${imageId}/analyze`,
      data || {},
    )
    return response.data
  },

  analyzeInspection: async (
    inspectionId: number,
    data?: { mm_per_pixel?: number },
  ): Promise<AnalyzeBatchResponse> => {
    const response = await apiClient.post<AnalyzeBatchResponse>(
      `/inspections/${inspectionId}/analyze`,
      data || {},
    )
    return response.data
  },

  getImageAnalysis: async (imageId: number): Promise<AnalysisRun | null> => {
    try {
      const response = await apiClient.get<AnalysisRun>(
        `/images/${imageId}/analysis`,
      )
      return response.data
    } catch (err: any) {
      if (err.response && err.response.status === 404) {
        return null
      }
      throw err
    }
  },

  getMaskBlobUrl: async (runId: number): Promise<string> => {
    const response = await apiClient.get(`/analysis/${runId}/mask`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  setScale: async (imageId: number, data: SetScaleRequest): Promise<ImageScale> => {
    const response = await apiClient.put<ImageScale>(`/images/${imageId}/scale`, data)
    return response.data
  },

  getScale: async (imageId: number): Promise<ImageScale | null> => {
    try {
      const response = await apiClient.get<ImageScale>(`/images/${imageId}/scale`)
      return response.data
    } catch (err: any) {
      if (err.response && err.response.status === 404) {
        return null
      }
      throw err
    }
  },

  deleteScale: async (imageId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/images/${imageId}/scale`)
    return response.data
  },

  remeasure: async (imageId: number): Promise<AnalysisRun> => {
    const response = await apiClient.post<AnalysisRun>(`/images/${imageId}/remeasure`)
    return response.data
  },
}

export interface FactorDetail {
  factor: string
  input_value: any
  points: number
  note?: string | null
}

export interface SeverityAssessment {
  assessment_id: number
  run_id: number
  image_id: number
  severity_level: 'none' | 'minor' | 'moderate' | 'severe' | 'critical'
  score: number
  priority_suggestion: string
  factors_json: string
  warnings_json?: string | null
  rules_version: string
  rules_sha256: string
  review_status: 'pending' | 'confirmed' | 'corrected'
  reviewed_by?: number | null
  reviewed_at?: string | null
  final_severity?: 'none' | 'minor' | 'moderate' | 'severe' | 'critical' | null
  final_priority?: string | null
  review_comment?: string | null
  is_superseded: boolean
  created_at: string
  factors?: FactorDetail[]
  warnings?: string[]
  needs_review: boolean
  low_confidence_review: boolean
}

export interface InspectionSeveritySummary {
  counts: Record<string, number>
  worst_severity: string
  worst_score: number
  images_assessed: number
  images_pending_review: number
  aggregation_rule: string
}

export interface InspectionSeverityDetail {
  inspection_id: number
  worst_severity: string
  worst_score: number
  images_assessed: number
  images_pending_review: number
  summary?: InspectionSeveritySummary
  assessments: SeverityAssessment[]
}

export interface SeverityRules {
  rules_version: string
  status: string
  rules_sha256: string
  rules: any
}

export const severityApi = {
  getImageSeverity: async (imageId: number): Promise<SeverityAssessment | null> => {
    try {
      const response = await apiClient.get<SeverityAssessment>(`/images/${imageId}/severity`)
      return response.data
    } catch (err: any) {
      if (err.response && err.response.status === 404) {
        return null
      }
      throw err
    }
  },

  getInspectionSeverity: async (inspectionId: number): Promise<InspectionSeverityDetail | null> => {
    try {
      const response = await apiClient.get<InspectionSeverityDetail>(`/inspections/${inspectionId}/severity`)
      return response.data
    } catch (err: any) {
      if (err.response && err.response.status === 404) {
        return null
      }
      throw err
    }
  },

  recompute: async (imageId: number): Promise<SeverityAssessment> => {
    const response = await apiClient.post<SeverityAssessment>(`/images/${imageId}/severity/recompute`)
    return response.data
  },

  review: async (
    assessmentId: number,
    data: {
      action: 'confirm' | 'correct'
      final_severity?: string
      final_priority?: string
      comment?: string
    },
  ): Promise<SeverityAssessment> => {
    const response = await apiClient.put<SeverityAssessment>(`/severity/${assessmentId}/review`, data)
    return response.data
  },

  getRules: async (): Promise<SeverityRules> => {
    const response = await apiClient.get<SeverityRules>('/severity/rules')
    return response.data
  },
}

export interface ExplanationMetadata {
  model_name?: string
  method?: string
  target_layer?: string
  target_description?: string
  image_size?: [number, number]
  inference_size?: [number, number]
  min_before_normalisation?: number
  max_before_normalisation?: number
  normalised_per_image?: boolean
  seconds?: number
  experimental?: boolean
  rtdetr_ran?: boolean
  warnings?: string[]
}

export interface ExplanationItem {
  explanation_id: number
  run_id: number
  image_id: number
  model_id: string
  method: string
  target: string
  heatmap_path?: string | null
  overlay_path?: string | null
  overlay_url?: string | null
  heatmap_url?: string | null
  params?: ExplanationMetadata | null
  warnings?: string[] | null
  seconds?: number | null
  status: 'pending' | 'in_progress' | 'done' | 'failed'
  error_message?: string | null
  created_at: string
}

export interface CompareMapsResult {
  explanation_id_a: number
  explanation_id_b: number
  spearman_correlation: number
  top_10_overlap: number
  interpretation: string
}

export const explainApi = {
  triggerExplain: async (
    imageId: number,
    payload?: { models?: string[]; methods?: string[] },
  ): Promise<ExplanationItem[]> => {
    const response = await apiClient.post<ExplanationItem[]>(`/images/${imageId}/explain`, payload || {})
    return response.data
  },

  getImageExplanations: async (imageId: number): Promise<ExplanationItem[]> => {
    const response = await apiClient.get<ExplanationItem[]>(`/images/${imageId}/explanations`)
    return response.data
  },

  getOverlayBlobUrl: async (explanationId: number): Promise<string> => {
    const response = await apiClient.get(`/explanations/${explanationId}/overlay`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  getHeatmapBlobUrl: async (explanationId: number): Promise<string> => {
    const response = await apiClient.get(`/explanations/${explanationId}/heatmap`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  compareMaps: async (explanationIdA: number, explanationIdB: number): Promise<CompareMapsResult> => {
    const response = await apiClient.post<CompareMapsResult>('/explanations/compare', {
      explanation_id_a: explanationIdA,
      explanation_id_b: explanationIdB,
    })
    return response.data
  },

  downloadOverlay: async (explanationId: number, filename = 'attention_overlay.png'): Promise<void> => {
    const response = await apiClient.get(`/explanations/${explanationId}/overlay`, {
      responseType: 'blob',
    })
    const blobUrl = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(blobUrl)
  },
}

// -----------------------------------------------------------------------------
// Damage Map & Geospatial API
// -----------------------------------------------------------------------------
export interface MapAssetProperties {
  id: number
  name: string
  type: string
  material: string
  district: string
  current_condition: {
    severity: string
    score: number | null
    provisional: boolean | null
    pending_review_count: number | null
    last_inspection_date: string | null
  }
  latest_inspection_id: number | null
  priority: string | null
  overdue: boolean
}

export interface MapDamageProperties {
  assessment_id: number
  image_id: number
  inspection_id: number
  asset_id: number
  asset_name: string
  severity: string
  score: number | null
  provisional: boolean | null
  damage_types: string[]
  detection_count: number
  date: string
  location_source: 'image_exif' | 'asset'
}

export interface MapFeature<P = any> {
  type: 'Feature'
  geometry: {
    type: 'Point'
    coordinates: [number, number] // [lon, lat]
  }
  properties: P
}

export interface MapFeatureCollection<P = any> {
  type: 'FeatureCollection'
  features: MapFeature<P>[]
  metadata?: {
    total: number
    limit: number
    offset: number
  }
}

export interface HotspotCell {
  cell_centre: [number, number] // [lat, lon]
  count: number
  mean_score: number
  max_severity: string
}

export interface HotspotsResponse {
  points: { lat: number; lon: number; weight: number; score: number; severity: string }[]
  grid: HotspotCell[]
  grid_size: number
  total_points: number
}

export interface RegionSummary {
  region: string
  total_assets: number
  counts_per_severity: Record<string, number>
  mean_score: number
  number_overdue: number
  number_pending_review: number
}

export interface MapSummaryResponse {
  regions: RegionSummary[]
  total_regions: number
}

export interface RouteStop {
  stop_number: number
  asset_id: number
  asset_name: string
  asset_type: string
  inspection_id: number
  lat: number
  lon: number
  district: string
}

export interface RouteResponse {
  inspector_id: number
  date: string
  ordered_stops: RouteStop[]
  total_distance_km: number
  distance_label: string
  message?: string
}

export const mapApi = {
  getAssets: async (params?: Record<string, any>): Promise<MapFeatureCollection<MapAssetProperties>> => {
    const response = await apiClient.get<MapFeatureCollection<MapAssetProperties>>('/map/assets', { params })
    return response.data
  },

  getDamage: async (params?: Record<string, any>): Promise<MapFeatureCollection<MapDamageProperties>> => {
    const response = await apiClient.get<MapFeatureCollection<MapDamageProperties>>('/map/damage', { params })
    return response.data
  },

  getHotspots: async (params?: Record<string, any>): Promise<HotspotsResponse> => {
    const response = await apiClient.get<HotspotsResponse>('/map/hotspots', { params })
    return response.data
  },

  getSummary: async (): Promise<MapSummaryResponse> => {
    const response = await apiClient.get<MapSummaryResponse>('/map/summary')
    return response.data
  },

  getRoute: async (inspectorId: number, dateStr: string): Promise<RouteResponse> => {
    const response = await apiClient.get<RouteResponse>('/map/route', {
      params: { inspector_id: inspectorId, date: dateStr },
    })
    return response.data
  },
}

// ---------------------------------------------------------------------------
// Reports & Exports API
// ---------------------------------------------------------------------------

export interface ReportFileItem {
  file_id: number
  format: 'pdf' | 'csv' | 'xlsx' | 'json' | string
  path: string
  size: number
  sha256: string
}

export interface ReportItem {
  report_id: number
  inspection_id: number
  version: number
  status: 'draft' | 'final' | string
  generated_by: number
  generated_at: string
  content_sha256: string
  notes?: string
  files: ReportFileItem[]
  is_final: boolean
}

export interface PaginatedReportsResponse {
  items: ReportItem[]
  total: number
  page: number
  page_size: number
}

export const reportsApi = {
  listReports: async (params?: {
    inspection_id?: number
    status?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedReportsResponse> => {
    const response = await apiClient.get<PaginatedReportsResponse>('/reports', { params })
    return response.data
  },

  getReport: async (reportId: number): Promise<ReportItem> => {
    const response = await apiClient.get<ReportItem>(`/reports/${reportId}`)
    return response.data
  },

  generateReport: async (inspectionId: number, notes?: string): Promise<ReportItem> => {
    const response = await apiClient.post<ReportItem>(`/inspections/${inspectionId}/reports`, {
      notes,
    })
    return response.data
  },

  downloadReport: async (reportId: number, format: 'pdf' | 'csv' | 'xlsx' | 'json') => {
    const response = await apiClient.get(`/reports/${reportId}/download`, {
      params: { format },
      responseType: 'blob',
    })
    const blob = new Blob([response.data], {
      type: String(response.headers['content-type'] || 'application/octet-stream'),
    })
    const url = window.URL.createObjectURL(blob)
    const contentDisposition = String(response.headers['content-disposition'] || '')
    let fileName = `report_${reportId}.${format === 'csv' ? 'zip' : format}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^";]+)"?/)
      if (match && match[1]) {
        fileName = match[1]
      }
    }
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  exportAsset: async (assetId: number, format: 'csv' | 'xlsx' = 'csv') => {
    const response = await apiClient.get(`/assets/${assetId}/export`, {
      params: { format },
      responseType: 'blob',
    })
    const blob = new Blob([response.data], {
      type: String(response.headers['content-type'] || 'application/octet-stream'),
    })
    const url = window.URL.createObjectURL(blob)
    const contentDisposition = String(response.headers['content-disposition'] || '')
    let fileName = `asset_${assetId}_summary.${format}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^";]+)"?/)
      if (match && match[1]) {
        fileName = match[1]
      }
    }
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  exportPortfolio: async (format: 'csv' | 'xlsx' = 'csv') => {
    const response = await apiClient.get('/exports/portfolio', {
      params: { format },
      responseType: 'blob',
    })
    const blob = new Blob([response.data], {
      type: String(response.headers['content-type'] || 'application/octet-stream'),
    })
    const url = window.URL.createObjectURL(blob)
    const contentDisposition = String(response.headers['content-disposition'] || '')
    let fileName = `infrascan_portfolio_summary.${format}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^";]+)"?/)
      if (match && match[1]) {
        fileName = match[1]
      }
    }
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

// ---------------------------------------------------------------------------
// Notifications & Alerts API
// ---------------------------------------------------------------------------

export interface NotificationItem {
  id: number
  user_id: number
  type: string
  title: string
  body: string
  entity_type?: string
  entity_id?: string
  read_at?: string
  email_sent: boolean
  email_sent_at?: string
  created_at: string
  is_read: boolean
}

export interface NotificationListResponse {
  items: NotificationItem[]
  total: number
  unread_count: number
  page: number
  page_size: number
}

export interface NotificationPreference {
  user_id: number
  in_app_enabled: boolean
  email_enabled: boolean
  min_severity: string
  updated_at: string
}

export const notificationsApi = {
  listNotifications: async (params?: {
    unread_only?: boolean
    page?: number
    page_size?: number
  }): Promise<NotificationListResponse> => {
    const response = await apiClient.get<NotificationListResponse>('/notifications', { params })
    return response.data
  },

  getUnreadCount: async (): Promise<{ unread_count: number }> => {
    const response = await apiClient.get<{ unread_count: number }>('/notifications/unread-count')
    return response.data
  },

  markRead: async (notificationId: number): Promise<NotificationItem> => {
    const response = await apiClient.post<NotificationItem>(`/notifications/${notificationId}/read`)
    return response.data
  },

  markAllRead: async (): Promise<{ marked_read: number }> => {
    const response = await apiClient.post<{ marked_read: number }>('/notifications/read-all')
    return response.data
  },

  getPreferences: async (): Promise<NotificationPreference> => {
    const response = await apiClient.get<NotificationPreference>('/notifications/preferences')
    return response.data
  },

  updatePreferences: async (data: Partial<NotificationPreference>): Promise<NotificationPreference> => {
    const response = await apiClient.put<NotificationPreference>('/notifications/preferences', data)
    return response.data
  },

  triggerSweep: async (): Promise<{ maintenance_alerts: number; overdue_inspections: number }> => {
    const response = await apiClient.post<{ maintenance_alerts: number; overdue_inspections: number }>('/notifications/sweep')
    return response.data
  },
}

export interface ModelVersionItem {
  model_id: string
  model_name: string
  task: string
  version: string
  weights_path: string
  threshold: number
  class_names?: Record<string, string> | null
  metrics?: Record<string, any> | null
  is_active: boolean
  inferences_count: number
  mean_inference_time_ms: number
  last_inference_at?: string | null
  error_count: number
  created_at: string
}

export interface ModelEventItem {
  id: number
  model_id: string
  event_type: string
  performed_by?: number | null
  details?: Record<string, any> | null
  created_at: string
}

export interface DatasetVersionItem {
  id: number
  name: string
  version: string
  task: string
  split_stats?: Record<string, any> | null
  created_at: string
}

export interface ClassifyCropResponse {
  crack_probability: number
  is_cracked: boolean
  label: string
  threshold: number
  model_id: string
  crop_dimensions: { width: number; height: number }
  latency_ms: number
  screening_disclaimer: string
}

export const modelsApi = {
  list: async (params?: { task?: string }): Promise<ModelVersionItem[]> => {
    const response = await apiClient.get<ModelVersionItem[]>('/models/registry', { params })
    return response.data
  },

  get: async (modelId: string): Promise<ModelVersionItem> => {
    const response = await apiClient.get<ModelVersionItem>(`/models/${modelId}`)
    return response.data
  },

  datasets: async (): Promise<DatasetVersionItem[]> => {
    const response = await apiClient.get<DatasetVersionItem[]>('/models/datasets')
    return response.data
  },

  events: async (modelId: string): Promise<ModelEventItem[]> => {
    const response = await apiClient.get<ModelEventItem[]>(`/models/${modelId}/events`)
    return response.data
  },

  activate: async (modelId: string): Promise<ModelVersionItem> => {
    const response = await apiClient.post<ModelVersionItem>(`/models/${modelId}/activate`)
    return response.data
  },

  rollback: async (modelId: string): Promise<ModelVersionItem> => {
    const response = await apiClient.post<ModelVersionItem>(`/models/${modelId}/rollback`)
    return response.data
  },

  classifyCrop: async (formData: FormData): Promise<ClassifyCropResponse> => {
    const response = await apiClient.post<ClassifyCropResponse>('/classify-crop', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
}

export interface JobItem {
  id: number
  job_type: string
  status: string
  progress: number
  payload: Record<string, any>
  result?: Record<string, any> | null
  error_message?: string | null
  retries: number
  max_retries: number
  user_id?: number | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
}

export interface JobListResponse {
  jobs: JobItem[]
  total: number
  page: number
  page_size: number
}

export const jobsApi = {
  enqueue: async (data: { job_type: string; payload: Record<string, any>; max_retries?: number }): Promise<JobItem> => {
    const response = await apiClient.post<JobItem>('/jobs', data)
    return response.data
  },

  list: async (params?: {
    status?: string
    job_type?: string
    page?: number
    page_size?: number
  }): Promise<JobListResponse> => {
    const response = await apiClient.get<JobListResponse>('/jobs', { params })
    return response.data
  },

  get: async (jobId: number): Promise<JobItem> => {
    const response = await apiClient.get<JobItem>(`/jobs/${jobId}`)
    return response.data
  },

  cancel: async (jobId: number): Promise<JobItem> => {
    const response = await apiClient.post<JobItem>(`/jobs/${jobId}/cancel`)
    return response.data
  },
}

export const eventsApi = {
  getTicket: async (): Promise<{ ticket: string; expires_in: number; user_id: number; role: string }> => {
    const response = await apiClient.post('/events/ticket')
    return response.data
  },

  getStreamUrl: (ticket: string, lastEventId?: number): string => {
    let url = `${API_BASE_URL}/events/stream?ticket=${encodeURIComponent(ticket)}`
    if (lastEventId && lastEventId > 0) {
      url += `&last_event_id=${lastEventId}`
    }
    return url
  },

  poll: async (sinceId: number = 0): Promise<{ events: any[]; last_id: number; count: number }> => {
    const response = await apiClient.get('/events/poll', { params: { since_id: sinceId } })
    return response.data
  },
}

export const maintenanceApi = {
  listTasks: async (params?: { asset_id?: number; status?: string }): Promise<any[]> => {
    const response = await apiClient.get('/maintenance/tasks', { params })
    return response.data
  },

  createTask: async (data: {
    asset_id: number
    inspection_id?: number
    priority_id?: number
    title: string
    description?: string
    task_type?: string
    priority?: string
    assigned_to?: number
    due_date?: string
  }): Promise<any> => {
    const response = await apiClient.post('/maintenance/tasks', data)
    return response.data
  },

  updateStatus: async (taskId: number, status: string, notes?: string): Promise<any> => {
    const response = await apiClient.put(`/maintenance/tasks/${taskId}/status`, { status, notes })
    return response.data
  },

  verifyTask: async (taskId: number, verified: boolean, comment?: string): Promise<any> => {
    const response = await apiClient.put(`/maintenance/tasks/${taskId}/verify`, { verified, comment })
    return response.data
  },

  confirmPriority: async (priorityId: number, finalPriority: string, comment?: string): Promise<any> => {
    const response = await apiClient.post(`/maintenance/priorities/${priorityId}/confirm`, {
      final_priority: finalPriority,
      comment,
    })
    return response.data
  },
}

export const comparisonsApi = {
  compare: async (prevInspectionId: number, currInspectionId: number): Promise<any> => {
    const response = await apiClient.post('/inspections/compare', {
      prev_inspection_id: prevInspectionId,
      curr_inspection_id: currInspectionId,
    })
    return response.data
  },

  listByInspection: async (inspectionId: number): Promise<any[]> => {
    const response = await apiClient.get(`/inspections/${inspectionId}/comparisons`)
    return response.data
  },

  get: async (comparisonId: number): Promise<any> => {
    const response = await apiClient.get(`/comparisons/${comparisonId}`)
    return response.data
  },
}

export const dashboardApi = {
  getAttention: async (): Promise<{
    role: string
    items: Array<{
      id: string
      category: string
      title: string
      description: string
      severity: string
      link: string
      created_at: string | null
    }>
    count: number
    disclaimer: string
  }> => {
    const response = await apiClient.get('/dashboard/attention')
    return response.data
  },
}
