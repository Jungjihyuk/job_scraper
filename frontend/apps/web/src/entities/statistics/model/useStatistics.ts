import { useEffect, useState } from 'react'
import {
  fetchSpecialtyByLocation,
  fetchExperienceBySpecialty,
  fetchPostingTrends,
  fetchAvailableYears,
} from '../api/statisticsApi'
import { transformStackedBar, transformHorizontalBar, transformLineChart } from '../lib/transforms'
import type { StackedBarData, LineChartData } from './types'

type ChartHookResult<T> = { data: T; loading: boolean; error: string | null }

export function useSpecialtyByLocation(): ChartHookResult<StackedBarData> {
  const [data, setData] = useState<StackedBarData>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const raw = await fetchSpecialtyByLocation()
        setData(transformStackedBar(raw))
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return { data, loading, error }
}

export function useExperienceBySpecialty(): ChartHookResult<StackedBarData> {
  const [data, setData] = useState<StackedBarData>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const raw = await fetchExperienceBySpecialty()
        setData(transformHorizontalBar(raw))
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return { data, loading, error }
}

export function usePostingTrends(
  specialty?: string,
  year?: number,
): ChartHookResult<LineChartData> & { years: number[] } {
  const [data, setData] = useState<LineChartData>([])
  const [years, setYears] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [trendsRaw, yearsData] = await Promise.all([
          fetchPostingTrends({ job_specialty: specialty, year }),
          fetchAvailableYears(),
        ])
        setData(transformLineChart(trendsRaw))
        setYears(yearsData.years)
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [specialty, year])

  return { data, years, loading, error }
}
