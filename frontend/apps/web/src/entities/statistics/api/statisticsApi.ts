import { getJson } from '../../../shared/api'
import type { ChartResponse, AvailableYearsResponse } from '../../../shared/api'

export async function fetchSpecialtyByLocation(): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/specialty_by_location')
}

export async function fetchExperienceBySpecialty(): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/experience_by_specialty')
}

export async function fetchPostingTrends(params?: {
  job_specialty?: string
  year?: number
}): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/posting_trends', {
    job_specialty: params?.job_specialty,
    year: params?.year,
  })
}

export async function fetchAvailableYears(): Promise<AvailableYearsResponse> {
  return getJson<AvailableYearsResponse>('/api/statistics/available_years')
}
