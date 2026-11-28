import { apiClient, extractApiError } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_ASSETS, MOCK_INSPECTIONS } from '@/data/mockData'
import type { InfrastructureAsset, Inspection } from '@/types'

let assetsStore = [...MOCK_ASSETS]

/** Map backend AssetOut shape to the frontend InfrastructureAsset type */
function mapApiAsset(a: Record<string, unknown>): InfrastructureAsset {
  const lat = (a.latitude as number) ?? 0
  const lng = (a.longitude as number) ?? 0
  return {
    id: a.id as string,
    assetCode: a.asset_code as string,
    name: a.name as string,
    type: a.infrastructure_type as InfrastructureAsset['type'],
    description: a.description as string | undefined,
    location: a.location_name as string,
    coordinates: [lat, lng],
    constructionYear: (a.construction_year as number) ?? 0,
    materialType: (a.material_type as string) ?? 'Unknown',
    owner: a.owner as string | undefined,
    responsibleDepartment: 'Infrastructure Division',
    inspectionFrequency: 'Annual',
    status: (a.asset_status === 'Active' ? 'Operational' : a.asset_status === 'Archived' ? 'Archived' : 'Operational') as InfrastructureAsset['status'],
    operationalStatus: a.asset_status as InfrastructureAsset['operationalStatus'],
    lastInspectionDate: (a.created_at as string) ?? new Date().toISOString(),
    conditionScore: 85,
    activeFindingsCount: 0,
  }
}

export const infrastructureService = {
  async getAll(): Promise<InfrastructureAsset[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 180))
      return [...assetsStore]
    }
    try {
      const { data } = await apiClient.get('/assets')
      return (data as Record<string, unknown>[]).map(mapApiAsset)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async getById(id: string): Promise<InfrastructureAsset | undefined> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 120))
      return assetsStore.find((a) => a.id === id)
    }
    try {
      const { data } = await apiClient.get(`/assets/${id}`)
      return mapApiAsset(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async create(
    asset: Omit<InfrastructureAsset, 'id' | 'conditionScore' | 'activeFindingsCount'>
  ): Promise<InfrastructureAsset> {
    if (API_CONFIG.enableMockData) {
      const nextNum = String(assetsStore.length + 1).padStart(4, '0')
      const created: InfrastructureAsset = {
        ...asset,
        id: `INF-${nextNum}`,
        assetCode: `INF-${nextNum}`,
        conditionScore: 92,
        activeFindingsCount: 0,
      }
      assetsStore = [created, ...assetsStore]
      return created
    }
    try {
      const payload = {
        asset_code: asset.assetCode || `INF-${Date.now()}`,
        name: asset.name,
        infrastructure_type: asset.type,
        location_name: asset.location,
        latitude: asset.coordinates?.[0],
        longitude: asset.coordinates?.[1],
        construction_year: asset.constructionYear,
        material_type: asset.materialType,
        owner: asset.owner,
        description: asset.description,
      }
      const { data } = await apiClient.post('/assets', payload)
      return mapApiAsset(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async update(id: string, patch: Partial<InfrastructureAsset>): Promise<InfrastructureAsset> {
    if (API_CONFIG.enableMockData) {
      assetsStore = assetsStore.map((a) => (a.id === id ? { ...a, ...patch } : a))
      return assetsStore.find((a) => a.id === id)!
    }
    try {
      const payload: Record<string, unknown> = {}
      if (patch.name) payload.name = patch.name
      if (patch.type) payload.infrastructure_type = patch.type
      if (patch.location) payload.location_name = patch.location
      if (patch.status) payload.asset_status = patch.status
      if (patch.description) payload.description = patch.description
      const { data } = await apiClient.patch(`/assets/${id}`, payload)
      return mapApiAsset(data as Record<string, unknown>)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async archive(id: string): Promise<void> {
    if (API_CONFIG.enableMockData) {
      assetsStore = assetsStore.map((a) =>
        a.id === id ? { ...a, status: 'Archived' as const, operationalStatus: 'Archived' as const } : a
      )
      return
    }
    try {
      await apiClient.delete(`/assets/${id}`)
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },

  async getInspectionHistory(assetId: string): Promise<Inspection[]> {
    if (API_CONFIG.enableMockData) {
      return MOCK_INSPECTIONS.filter((i) => i.assetId === assetId)
    }
    try {
      const { data } = await apiClient.get(`/inspections?asset_id=${assetId}`)
      return data as Inspection[]
    } catch (err) {
      throw new Error(extractApiError(err))
    }
  },
}
