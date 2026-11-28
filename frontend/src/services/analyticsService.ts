import { apiClient } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import {
  MONTHLY_INSPECTION_TRENDS,
  DAMAGE_CATEGORY_DISTRIBUTION,
  SEVERITY_DISTRIBUTION,
  MODEL_PERFORMANCE_METRICS,
} from '@/data/mockData'

export const analyticsService = {
  async getOverview() {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 180))
      return {
        monthlyTrends: MONTHLY_INSPECTION_TRENDS,
        damageCategories: DAMAGE_CATEGORY_DISTRIBUTION,
        severityDistribution: SEVERITY_DISTRIBUTION,
        modelPerformance: MODEL_PERFORMANCE_METRICS,
      }
    }
    const { data } = await apiClient.get('/analytics/overview')
    return data
  },
}

