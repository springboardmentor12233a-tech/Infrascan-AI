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
