import type { InfrastructureType, SeverityLevel, InspectionStatus, MaintenancePriority, UserRole } from '@/types'

export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  enableMockData: import.meta.env.VITE_ENABLE_MOCK_DATA !== 'false',
  timeoutMs: 15000,
}

export const INFRASTRUCTURE_TYPES: InfrastructureType[] = [
  'Bridge',
  'Building',
  'Road',
  'Tunnel',
  'Dam',
  'Concrete Structure',
  'Retaining Wall',
  'Industrial Structure',
]

export const SEVERITY_LEVELS: SeverityLevel[] = ['Low', 'Moderate', 'High', 'Critical']

export const INSPECTION_STATUSES: InspectionStatus[] = [
  'Draft',
  'Pending',
  'Processing',
  'Completed',
  'Requires Review',
]

export const MAINTENANCE_PRIORITIES: MaintenancePriority[] = [
  'Routine Monitoring',
  'Low Priority',
  'Medium Priority',
  'High Priority',
  'Urgent Engineering Review',
]

export const USER_ROLES: UserRole[] = [
  'Civil Engineer',
  'Infrastructure Inspector',
  'Maintenance Engineer',
  'Infrastructure Manager',
  'Administrator',
]

export const DEMO_DISCLAIMER =
  'Demonstration Data: AI predictions, crack measurements, and geospatial coordinates shown here are simulated for frontend evaluation prior to FastAPI/PyTorch backend integration.'

