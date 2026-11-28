import { apiClient } from './apiClient'
import { API_CONFIG } from '@/lib/constants'
import { MOCK_NOTIFICATIONS } from '@/data/mockData'
import type { AppNotification } from '@/types'

export const notificationService = {
  async getAll(): Promise<AppNotification[]> {
    if (API_CONFIG.enableMockData) {
      await new Promise((r) => setTimeout(r, 150))
      return [...MOCK_NOTIFICATIONS]
    }
    const { data } = await apiClient.get('/notifications')
    return data
  },
}

