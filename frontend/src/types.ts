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
  images?: InspectionImage[];
}

export type QualityStatus = 'ok' | 'blurry' | 'low_light' | 'overexposed';

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
  has_crack?: boolean;
  confidence_score?: number;
  severity_level?: 'None' | 'Low' | 'Medium' | 'High' | 'Critical';
  crack_type?: string;
  crack_length_px?: number;
  max_crack_width_px?: number;
  avg_crack_width_px?: number;
  crack_density_pct?: number;
  crack_area_px?: number;
  crack_length_mm?: number;
  max_crack_width_mm?: number;
  avg_crack_width_mm?: number;
  crack_area_mm2?: number;
  orientation_deg?: number;
  branching_points?: number;
  calibration_mm_per_px?: number;
  bounding_boxes?: string;
  uploaded_at: string;
  url?: string;
  damage_types?: string;  // JSON string of DamageTypeItem[]
  risk_score?: number;
}

export interface DamageTypeItem {
  damage_type: string;
  confidence: number;
  severity: string;
  boxes?: Array<{ xmin: number; ymin: number; xmax: number; ymax: number; label: string; confidence: number }>;
}

export interface MaintenanceQueueItem {
  asset_id: number;
  asset_code: string;
  asset_name: string;
  asset_type: string;
  location: string;
  latitude?: number;
  longitude?: number;
  risk_score: number;
  priority: string;
  recommended_action: string;
  max_severity: string;
  crack_count: number;
  total_images: number;
  damage_types_found: string[];
  last_inspection_date?: string;
  construction_year?: number;
}

export interface WorkOrder {
  id: number;
  asset_id: number;
  inspection_id?: number;
  assigned_to_id?: number;
  title: string;
  description: string;
  priority: 'Routine Monitoring' | 'Low Priority' | 'Medium Priority' | 'High Priority' | 'Urgent Engineering Review';
  status: 'Open' | 'In Progress' | 'Resolved' | 'Cancelled';
  estimated_cost?: number;
  due_date?: string;
  resolution_notes?: string;
  created_at: string;
  resolved_at?: string;
  asset_code?: string;
  asset_name?: string;
  assigned_to_name?: string;
}

export interface NotificationItem {
  id: number;
  user_id?: number;
  target_role?: string;
  title: string;
  message: string;
  alert_level: 'Informational' | 'Low' | 'Medium' | 'High' | 'Critical';
  link?: string;
  is_read: boolean;
  created_at: string;
}

export interface DashboardAnalytics {
  total_assets: number;
  total_inspections: number;
  total_images: number;
  cracked_images: number;
  crack_rate_pct: number;
  severity_distribution: Record<string, number>;
  inspection_status: Record<string, number>;
  recent_inspections: Array<{
    id: number;
    asset_id: number;
    asset_name: string;
    inspection_date: string;
    status: string;
    inspector_name: string;
  }>;
  asset_type_distribution: Record<string, number>;
}

export interface ModelComparisonItem {
  id?: string;
  name: string;
  version?: string;
  type: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  inference_time_ms: number;
  model_size_kb: number;
  parameters: string;
  status: string;
  notes: string;
  is_active?: boolean;
}

export interface ProgressionTimelineItem {
  inspection_id: number;
  inspection_date?: string;
  status: string;
  inspector_name: string;
  total_images: number;
  cracked_images: number;
  max_severity: string;
  total_crack_length_px: number;
  total_crack_length_mm: number;
  max_crack_width_px: number;
  max_crack_width_mm: number;
  total_crack_area_px: number;
  mean_crack_density_pct: number;
  detected_damage_categories: string[];
  growth_rate_pct: number;
  progression_status: string;
}

export interface AssetProgressionData {
  asset_id: number;
  asset_code: string;
  asset_name: string;
  total_inspections: number;
  timeline: ProgressionTimelineItem[];
}

export interface InspectionComparisonData {
  current_inspection: {
    id: number;
    date?: string;
    summary: any;
  };
  previous_inspection: {
    id: number;
    date?: string;
    summary: any;
  };
  deltas: {
    crack_length_px_change: number;
    crack_length_mm_change: number;
    max_width_mm_change: number;
    cracked_images_change: number;
    new_defects_identified: string[];
    overall_progression_trend: string;
    alert_level: string;
  };
}
