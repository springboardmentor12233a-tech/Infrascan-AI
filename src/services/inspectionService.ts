import { apiClient, extractApiError } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_INSPECTIONS } from '@/data/mockData'
import type { Inspection, InfrastructureType } from '@/types'

let inspectionsStore: Inspection[] = MOCK_INSPECTIONS.map((i) => ({
  ...i,
  title: `${i.assetName} — ${i.assetType} Inspection`,
  type: 'Routine Inspection',
  aiStatus: i.status === 'Completed' ? 'Completed' : i.status === 'Processing' ? 'Processing' : 'Not Started',
}))

/** Map backend InspectionOut to frontend Inspection type */
function mapApiInspection(r: Record<string, unknown>): Inspection {
  return {
    id: r.id as string,
    assetId: r.asset_id as string,
    assetName: (r.asset_name as string) || 'Unknown Asset',
    assetType: ((r.asset_type as string) || 'Bridge') as InfrastructureType,
    title: `${r.inspection_code as string} — ${r.inspection_type as string}`,
    type: r.inspection_type as string,
    inspectorName: (r.inspector_name as string) || 'Unassigned',
    inspectorId: (r.inspector_id as string) || '',
    date: r.inspection_date as string,
    status: r.inspection_status as Inspection['status'],
    imageCount: 0,
    findingsCount: 0,
    maxSeverity: 'None',
    aiStatus: 'Not Started',
    notes: (r.inspection_notes as string) || '',
  }
}

export const inspectionService = {
  async getAll(): Promise<Inspection[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 180))
      return [...inspectionsStore]
    }
    try {
      const { data } = await apiClient.get('/inspections')
      return (data as Record<string, unknown>[]).map(mapApiInspection)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async getById(id: string): Promise<Inspection | undefined> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 120))
      return inspectionsStore.find((i) => i.id === id)
    }
    try {
      const { data } = await apiClient.get(`/inspections/${id}`)
      return mapApiInspection(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async create(payload: Omit<Inspection, 'id' | 'findingsCount' | 'maxSeverity'>): Promise<Inspection> {
    if (API_CONFIG.enableMockData) {
      const nextNum = String(90 + inspectionsStore.length).padStart(3, '0')
      const created: Inspection = {
        ...payload,
        id: `INSP-2026-${nextNum}`,
        findingsCount: 0,
        maxSeverity: 'None',
        aiStatus: payload.imageCount > 0 ? 'Queued' : 'Not Started',
      }
      inspectionsStore = [created, ...inspectionsStore]
      return created
    }
    try {
      const apiPayload = {
        inspection_code: `INSP-${Date.now()}`,
        asset_id: payload.assetId,
        inspection_type: payload.type || 'Routine Inspection',
        inspection_date: payload.date,
        inspector_id: payload.inspectorId || undefined,
        inspection_notes: payload.notes || undefined,
      }
      const { data } = await apiClient.post('/inspections', apiPayload)
      return mapApiInspection(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async update(id: string, patch: Partial<Inspection>): Promise<Inspection> {
    if (API_CONFIG.enableMockData) {
      inspectionsStore = inspectionsStore.map((i) => (i.id === id ? { ...i, ...patch } : i))
      return inspectionsStore.find((i) => i.id === id)!
    }
    try {
      const apiPatch: Record<string, unknown> = {}
      if (patch.status) apiPatch.inspection_status = patch.status
      if (patch.notes) apiPatch.inspection_notes = patch.notes
      const { data } = await apiClient.patch(`/inspections/${id}`, apiPatch)
      return mapApiInspection(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async cancel(id: string): Promise<void> {
    if (API_CONFIG.enableMockData) {
      inspectionsStore = inspectionsStore.map((i) => (i.id === id ? { ...i, status: 'Cancelled' as const } : i))
      return
    }
    try {
      await apiClient.patch(`/inspections/${id}`, { inspection_status: 'Cancelled' })
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },
}
