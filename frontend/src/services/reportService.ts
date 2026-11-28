import { apiClient } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_REPORTS } from '@/data/mockData'
import type { InspectionReport } from '@/types'

let reportsStore = [...MOCK_REPORTS]

export const reportService = {
  async getAll(): Promise<InspectionReport[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 180))
      return [...reportsStore]
    }
    const { data } = await apiClient.get('/reports')
    return data
  },

  async generate(inspectionId: string, assetId: string, assetName: string): Promise<InspectionReport> {
    if (API_CONFIG.enableMockData) {
      const created: InspectionReport = {
        id: `RPT-2026-0${42 + reportsStore.length}`,
        title: `${assetName} — AI Inspection Report`,
        inspectionId,
        assetId,
        assetName,
        generatedAt: new Date().toISOString().slice(0, 10),
        generatedBy: 'Elena Vance, PE',
        engineerReviewStatus: 'Pending Review',
        findingsSummary: 'Generated from latest AI damage analysis & field notes.',
        maxSeverity: 'High',
        pageCount: 14,
      }
      reportsStore = [created, ...reportsStore]
      return created
    }
    const { data } = await apiClient.post('/reports/generate', { inspectionId })
    return data
  },
}

