export type InfrastructureType =
  | 'Bridge'
  | 'Building'
  | 'Road'
  | 'Tunnel'
  | 'Dam'
  | 'Concrete Structure'
  | 'Retaining Wall'
  | 'Industrial Structure'

export type AssetStatus = 'Operational' | 'Under Inspection' | 'Maintenance Required' | 'Critical' | 'Archived'

export type AssetCondition =
  | 'Good'
  | 'Minor Damage'
  | 'Moderate Damage'
  | 'Severe Visible Damage'
  | 'Requires Engineering Review'
  | 'Not Assessed'

export type AssetOperationalStatus = 'Active' | 'Inactive' | 'Under Maintenance' | 'Archived'

export type SeverityLevel = 'Low' | 'Moderate' | 'High' | 'Critical'

export type InspectionStatus = 'Draft' | 'Scheduled' | 'Pending' | 'In Progress' | 'Images Uploaded' | 'Processing' | 'Completed' | 'Requires Review' | 'Cancelled'

export type AiProcessingStatus = 'Not Started' | 'Queued' | 'Processing' | 'Completed' | 'Failed'

export type DamageCategory =
  | 'Longitudinal Crack'
  | 'Transverse Crack'
  | 'Alligator Crack'
  | 'Spalling'
  | 'Efflorescence'
  | 'Delamination'
  | 'Corrosion Staining'
  | 'Joint Deterioration'

export type MaintenancePriority =
  | 'Routine Monitoring'
  | 'Low Priority'
  | 'Medium Priority'
  | 'High Priority'
  | 'Urgent Engineering Review'

export type MaintenanceStatus = 'Open' | 'Scheduled' | 'In Progress' | 'Completed' | 'Deferred'

export type UserRole =
  | 'Civil Engineer'
  | 'Infrastructure Inspector'
  | 'Maintenance Engineer'
  | 'Infrastructure Manager'
  | 'Administrator'

export interface InfrastructureAsset {
  id: string
  assetCode?: string
  name: string
  type: InfrastructureType
  description?: string
  location: string
  district?: string
  city?: string
  state?: string
  country?: string
  address?: string
  postalCode?: string
  coordinates: [number, number] // [lat, lng] - clearly marked as demo coordinates
  constructionYear: number
  materialType: string
  secondaryMaterial?: string
  structuralSystem?: string
  floors?: number
  lengthMeters?: number
  widthMeters?: number
  heightMeters?: number
  responsibleDepartment: string
  owner?: string
  contactPerson?: string
  contactEmail?: string
  contactNumber?: string
  assignedInspector?: string
  inspectionFrequency: 'Monthly' | 'Quarterly' | 'Half-Yearly' | 'Semi-Annual' | 'Annual' | 'Annually' | 'Custom'
  status: AssetStatus
  condition?: AssetCondition
  operationalStatus?: AssetOperationalStatus
  lastInspectionDate: string
  nextInspectionDate?: string
  inspectionPriority?: string
  maintenanceNotes?: string
  conditionScore: number // 0-100
  activeFindingsCount: number
}

export interface Inspection {
  id: string
  title?: string
  type?: string
  assetId: string
  assetName: string
  assetType: InfrastructureType
  inspectorName: string
  inspectorId: string
  date: string
  time?: string
  priority?: string
  method?: string
  objective?: string
  location?: string
  status: InspectionStatus
  aiStatus?: AiProcessingStatus
  imageCount: number
  findingsCount: number
  maxSeverity: SeverityLevel | 'None'
  notes: string
}

export type ImageQualityStatus =
  | 'Good Quality'
  | 'Acceptable'
  | 'Blurry'
  | 'Low Resolution'
  | 'Poor Lighting'
  | 'Requires Review'

export type CalibrationStatus =
  | 'Not Calibrated'
  | 'Calibration Available'
  | 'Calibration Verified'
  | 'Calibration Required'

export interface InspectionImage {
  id: string
  filename: string
  url: string
  assetId: string
  assetName: string
  inspectionId: string
  uploadDate: string
  resolution: string
  fileSizeBytes: number
  cameraModel: string
  calibrated: boolean
  calibrationStatus?: CalibrationStatus
  pxPerMm?: number
  hasAiAnalysis: boolean
  processingStatus?: AiProcessingStatus
  qualityStatus?: ImageQualityStatus
  category?: string
  captureMethod?: string
  description?: string
  tags?: string[]
  severity?: SeverityLevel
}

export interface BoundingBox {
  id: string
  label: DamageCategory
  confidence: number
  x: number // percentage 0-100
  y: number // percentage 0-100
  width: number // percentage 0-100
  height: number // percentage 0-100
  severity: SeverityLevel
  estimatedLengthMm?: number
  estimatedWidthMm?: number
  areaMm2?: number
}

export interface SegmentationPolygon {
  id: string
  category: DamageCategory
  points: string // SVG polygon points in 0-1000 coordinate space
  color: string
  opacity: number
}

export interface AiAnalysisResult {
  id: string
  imageId: string
  imageName: string
  modelName: string
  modelVersion: string
  inferenceTimeMs: number
  isDemoData: true
  overallSeverity: SeverityLevel
  confidenceMean: number
  calibrated: boolean
  detections: BoundingBox[]
  segmentations: SegmentationPolygon[]
  summary: string
  recommendations: string[]
  analyzedAt: string
}

export interface MaintenanceTask {
  id: string
  title: string
  assetId: string
  assetName: string
  inspectionId?: string
  priority: MaintenancePriority
  status: MaintenanceStatus
  assignedTo: string
  dueDate: string
  createdAt: string
  estimatedCostUsd: number
  description: string
  followUpInspectionRequired: boolean
}

export interface InspectionReport {
  id: string
  title: string
  inspectionId: string
  assetId: string
  assetName: string
  generatedAt: string
  generatedBy: string
  engineerReviewStatus: 'Pending Review' | 'Approved' | 'Revision Requested'
  findingsSummary: string
  maxSeverity: SeverityLevel
  pageCount: number
}

export interface AppNotification {
  id: string
  type:
    | 'inspection_assigned'
    | 'inspection_completed'
    | 'damage_detected'
    | 'severe_damage'
    | 'review_required'
    | 'maintenance_deadline'
  title: string
  message: string
  timestamp: string
  read: boolean
  linkTo?: string
  severity?: SeverityLevel
}

export interface UserAccount {
  id: string
  name: string
  email: string
  role: UserRole
  department: string
  status: 'Active' | 'Inactive' | 'Pending'
  lastActive: string
  avatarInitials: string
}

