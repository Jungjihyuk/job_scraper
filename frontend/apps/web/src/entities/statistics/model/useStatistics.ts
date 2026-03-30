import { useEffect, useState } from 'react'
import {
  fetchSpecialtyByLocation,
  fetchExperienceBySpecialty,
  fetchPostingTrends,
  fetchAvailableYears,
  fetchDomainDistribution,
  fetchTechnologyTrends,
  fetchAvailableTechnologies,
  fetchCompanyTypeDistribution,
  fetchDomainByCompanyType,
  fetchTechnologyByCompanyType,
} from '../api/statisticsApi'
import { transformStackedBar, transformHorizontalBar, transformLineChart, transformTreemap } from '../lib/transforms'
import type { TreemapNode } from '../lib/transforms'
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

export function useDomainDistribution(): ChartHookResult<StackedBarData> {
  const [data, setData] = useState<StackedBarData>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const raw = await fetchDomainDistribution()
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

export function useCompanyTypeDistribution(): ChartHookResult<StackedBarData> {
  const [data, setData] = useState<StackedBarData>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const raw = await fetchCompanyTypeDistribution()
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

export function useDomainByCompanyType(): ChartHookResult<TreemapNode[]> {
  const [data, setData] = useState<TreemapNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const raw = await fetchDomainByCompanyType()
        setData(transformTreemap(raw))
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

export function useTechnologyByCompanyType(): ChartHookResult<StackedBarData> {
  const [data, setData] = useState<StackedBarData>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const raw = await fetchTechnologyByCompanyType()
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

export function useTechnologyTrends(
  technology?: string,
  year?: number,
): ChartHookResult<LineChartData> & { technologies: string[] } {
  const [data, setData] = useState<LineChartData>([])
  const [technologies, setTechnologies] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [trendsRaw, techData] = await Promise.all([
          fetchTechnologyTrends({ technology, year }),
          fetchAvailableTechnologies(),
        ])
        // For multi-line technology trends, transform differently
        if (trendsRaw.datasets.length > 1) {
          // Multi-dataset: return labels mapped to dataset values
          const result = trendsRaw.labels.map((label, i) => {
            const datum: Record<string, string | number> = { date: label }
            trendsRaw.datasets.forEach((ds) => {
              datum[ds.label] = ds.data[i] ?? 0
            })
            return datum
          })
          setData(result as unknown as LineChartData)
        } else {
          setData(transformLineChart(trendsRaw))
        }
        setTechnologies(techData.technologies)
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [technology, year])

  return { data, technologies, loading, error }
}
