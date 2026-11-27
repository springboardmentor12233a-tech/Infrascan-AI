import axios from 'axios'

// API base URL (defaults to '/api' so Vite proxy forwards seamlessly without CORS issues)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
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

// Response interceptor to handle 401 Unauthorized errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('user')

      if (
        !window.location.pathname.includes('/login') &&
        !window.location.pathname.includes('/register')
      ) {
        window.location.href = '/login'
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
  token_type: string
  role: string
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
    const response = await apiClient.get<User[]>('/users')
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

// ---------------- MILESTONE 3 & 4 INTERFACES ----------------

export interface DamageAssessment {
  assessment_id: number
  image_id: number
  inspection_id: number
  defect_type: string
  confidence: number
  bounding_box: any
  mask_path: string | null
  heatmap_path: string | null
  overlay_path: string | null
  crack_length_px: number
  avg_width_px: number
  max_width_px: number
  crack_density_percent: number
  crack_length_mm: number | null
  avg_width_mm: number | null
  max_width_mm: number | null
  orientation_deg: number
  severity_category: 'no_damage' | 'minor' | 'moderate' | 'severe' | 'critical'
  severity_score: number
  requires_urgent_review: boolean
  recommended_action: string
  created_at: string
}

export interface DamageProgression {
  current_inspection_id: number
  previous_inspection_id: number
  days_between: number
  growth_rate_pct: number
  length_change_px: number
  avg_width_change_px: number
  max_width_change_px: number
  deterioration_trend: 'stable' | 'minor' | 'moderate' | 'accelerated'
  summary: string
}

export interface MaintenanceRecommendation {
  recommendation_id: number
  asset_id: number
  inspection_id: number | null
  priority: 'routine_monitoring' | 'low' | 'medium' | 'high' | 'urgent_engineering_review'
  action_required: string
  recommended_technique: string | null
  estimated_cost_tier: string | null
  urgency_days: number
  status: 'pending' | 'scheduled' | 'in_progress' | 'completed'
  assigned_to: number | null
  notes: string | null
  created_at: string
}

export interface InspectionReport {
  report_id: number
  inspection_id: number
  generated_by: number | null
  report_format: 'pdf' | 'csv' | 'json'
  file_path: string
  file_size_bytes: number
  overall_condition_score: number
  summary_findings: string | null
  engineer_signoff: boolean
  signoff_notes: string | null
  created_at: string
}

export interface NotificationItem {
  notification_id: number
  user_id: number | null
  title: string
  message: string
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical'
  link: string | null
  is_read: boolean
  created_at: string
}

export interface DashboardStats {
  total_assets: number
  total_inspections: number
  completed_inspections: number
  total_images: number
  critical_findings: number
  avg_health_score: number
  severity_distribution: Record<string, number>
  defect_distribution: Record<string, number>
  recent_inspections: any[]
  hotspot_locations: any[]
}

// ---------------- MILESTONE 3 & 4 APIS ----------------

export const analysisApi = {
  analyze: async (
    imageId: number,
    mmPerPx?: number,
  ): Promise<DamageAssessment> => {
    const response = await apiClient.post<DamageAssessment>(
      `/images/${imageId}/analyze`,
      null,
      { params: mmPerPx ? { mm_per_px: mmPerPx } : {} },
    )
    return response.data
  },

  getAssessment: async (imageId: number): Promise<DamageAssessment> => {
    const response = await apiClient.get<DamageAssessment>(
      `/images/${imageId}/assessment`,
    )
    return response.data
  },

  getMaskBlobUrl: async (imageId: number): Promise<string> => {
    const response = await apiClient.get(`/images/${imageId}/mask`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  getHeatmapBlobUrl: async (imageId: number): Promise<string> => {
    const response = await apiClient.get(`/images/${imageId}/heatmap`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(response.data)
  },

  getInspectionSummary: async (
    inspectionId: number,
  ): Promise<{
    inspection_id: number
    total_assessments: number
    critical_defects: number
    avg_severity_score: number
    overall_severity_category: string
    assessments: DamageAssessment[]
  }> => {
    const response = await apiClient.get(
      `/inspections/${inspectionId}/assessment-summary`,
    )
    return response.data
  },
}

export const progressionApi = {
  compare: async (
    currentId: number,
    prevId: number,
  ): Promise<DamageProgression> => {
    const response = await apiClient.get<DamageProgression>(
      `/inspections/${currentId}/compare/${prevId}`,
    )
    return response.data
  },
}

export const maintenanceApi = {
  list: async (
    priority?: string,
    status?: string,
  ): Promise<MaintenanceRecommendation[]> => {
    const response = await apiClient.get<MaintenanceRecommendation[]>(
      '/maintenance/priorities',
      { params: { priority, status } },
    )
    return response.data
  },

  getAssetRecommendations: async (
    assetId: number,
  ): Promise<MaintenanceRecommendation[]> => {
    const response = await apiClient.get<MaintenanceRecommendation[]>(
      `/maintenance/asset/${assetId}`,
    )
    return response.data
  },

  updateStatus: async (
    id: number,
    status: string,
  ): Promise<MaintenanceRecommendation> => {
    const response = await apiClient.put<MaintenanceRecommendation>(
      `/maintenance/${id}/status`,
      null,
      { params: { status } },
    )
    return response.data
  },
}

export const reportsApi = {
  generate: async (
    inspectionId: number,
    format: 'pdf' | 'csv' | 'json' = 'pdf',
    summaryFindings?: string,
  ): Promise<InspectionReport> => {
    const response = await apiClient.post<InspectionReport>(
      `/inspections/${inspectionId}/reports/generate`,
      {
        report_format: format,
        summary_findings: summaryFindings,
      },
    )
    return response.data
  },

  list: async (inspectionId: number): Promise<InspectionReport[]> => {
    const response = await apiClient.get<InspectionReport[]>(
      `/inspections/${inspectionId}/reports`,
    )
    return response.data
  },

  getDownloadUrl: (reportId: number): string => {
    const token = localStorage.getItem('token') || ''
    return `${API_BASE_URL}/reports/${reportId}/download?token=${encodeURIComponent(token)}`
  },

  downloadFile: async (reportId: number, filename?: string): Promise<void> => {
    const response = await apiClient.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    })
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename || `report_${reportId}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

export const notificationsApi = {
  list: async (unreadOnly = false): Promise<NotificationItem[]> => {
    const response = await apiClient.get<NotificationItem[]>('/notifications', {
      params: { unread_only: unreadOnly },
    })
    return response.data
  },

  markRead: async (id: number): Promise<{ success: boolean }> => {
    const response = await apiClient.put<{ success: boolean }>(
      `/notifications/${id}/read`,
    )
    return response.data
  },
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get<DashboardStats>('/dashboard/stats')
    return response.data
  },
}

