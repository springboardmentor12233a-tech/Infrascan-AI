import axios from 'axios'

// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
