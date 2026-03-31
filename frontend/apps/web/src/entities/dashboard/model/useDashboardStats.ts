import { useEffect, useState } from 'react'
import { fetchDashboardStats } from '../api/dashboardApi'
import type { DashboardStats } from '../../../shared/api'

type UseDashboardStatsResult = {
  stats: DashboardStats | null
  loading: boolean
  error: string | null
}

export function useDashboardStats(): UseDashboardStatsResult {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchDashboardStats()
        setStats(data)
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return { stats, loading, error }
}
