import { getJson } from '../../../shared/api'
import type { DashboardStats } from '../../../shared/api'

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return getJson<DashboardStats>('/api/dashboard/stats')
}
