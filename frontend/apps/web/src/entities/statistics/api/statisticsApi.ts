import { getJson } from '../../../shared/api'
import type { ChartResponse, AvailableYearsResponse, AvailableTechnologiesResponse } from '../../../shared/api'

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

export async function fetchDomainDistribution(): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/domain_distribution')
}

export async function fetchTechnologyTrends(params?: {
  technology?: string
  year?: number
}): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/technology_trends', {
    technology: params?.technology,
    year: params?.year,
  })
}

export async function fetchAvailableTechnologies(): Promise<AvailableTechnologiesResponse> {
  return getJson<AvailableTechnologiesResponse>('/api/statistics/available_technologies')
}

export async function fetchCompanyTypeDistribution(): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/company_type_distribution')
}

export async function fetchDomainByCompanyType(): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/domain_by_company_type')
}

export async function fetchTechnologyByCompanyType(): Promise<ChartResponse> {
  return getJson<ChartResponse>('/api/statistics/technology_by_company_type')
}
