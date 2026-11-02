export type RoleName =
  | 'Administrator'
  | 'Infrastructure Manager'
  | 'Civil Engineer'
  | 'Infrastructure Inspector'
  | 'Maintenance Engineer';

export interface Role {
  id: number;
  name: RoleName;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role_id: number;
  role?: Role;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type AssetType =
  | 'Building'
  | 'Bridge'
  | 'Road'
  | 'Tunnel'
  | 'Dam'
  | 'Concrete Structure'
  | 'Retaining Wall'
  | 'Industrial Structure';

export interface InfrastructureAsset {
  id: number;
  asset_code: string;
  name: string;
  type: AssetType;
  location_text?: string;
  latitude?: number;
  longitude?: number;
  construction_year?: number;
  material_type?: string;
  responsible_department?: string;
  inspection_frequency_days?: number;
  maintenance_history?: string;
  created_at: string;
}

export interface AssetListResponse {
  total: number;
  page: number;
  size: number;
  items: InfrastructureAsset[];
}

export type InspectionStatus = 'pending' | 'in_progress' | 'completed';

export interface Inspection {
  id: number;
  asset_id: number;
  inspector_id: number;
  inspection_date: string;
  status: InspectionStatus;
  notes?: string;
  created_at: string;
  inspector?: User;
  asset?: InfrastructureAsset;
}

export type QualityStatus = 'ok' | 'blurry' | 'low_light';

export interface InspectionImage {
  id: number;
  inspection_id: number;
  file_path: string;
  original_filename: string;
  md5_hash: string;
  width: number;
  height: number;
  file_size_kb: number;
  blur_score?: number;
  brightness?: number;
  quality_status: QualityStatus;
  uploaded_at: string;
  url?: string;
}

export type AnalysisTaskStatus = 'completed' | 'unavailable' | 'failed';

export interface DetectionBox {
  class_id: number;
  class_name: string;
  confidence: number;
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
}

export interface CrackGeometry {
  crack_pixel_area: number;
  crack_length_px: number;
  crack_width_px_mean: number;
  crack_width_px_median: number;
  bbox_width_px: number;
  bbox_height_px: number;
  coverage_percent: number;
  unit: string;
  physical_scale_note: string;
}

export interface ImageAnalysis {
  id: number;
  image_id: number;
  inspection_id: number;
  quality: {
    valid: boolean;
    width: number;
    height: number;
    blur_score: number | null;
    brightness: number | null;
    contrast: number | null;
    status: string;
    flags: string[];
    notes: string[];
  };
  classification_status: AnalysisTaskStatus;
  classification_label?: string | null;
  classification_confidence?: number | null;
  classification: {
    status: AnalysisTaskStatus;
    label?: string | null;
    confidence?: number | null;
    detail?: string;
    crack_patch_fraction?: number;
    max_crack_probability?: number;
  };
  detection_status: AnalysisTaskStatus;
  detection: {
    status: AnalysisTaskStatus;
    model?: string;
    detail?: string;
    reliable?: boolean;
    validation_map50?: number | null;
    candidate_count?: number;
    detections?: DetectionBox[];
  };
  segmentation_status: AnalysisTaskStatus;
  segmentation: {
    status: AnalysisTaskStatus;
    model?: string;
    detail?: string;
  };
  geometry: {
    status: string;
    detail?: string;
    measurements: CrackGeometry | null;
  };
  overlay_url?: string | null;
  mask_url?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface ModelStatus {
  classifier: { name: string; available: boolean; task: string; framework?: string };
  segmentation: { name: string; available: boolean; task: string; framework?: string };
  detection: { name: string; available: boolean; task: string; framework?: string; note?: string };
}

export interface DashboardStats {
  assets: number;
  inspections: number;
  images: number;
  analyses: number;
}
