import { getJson } from '../../../shared/api'
import type { JobListResponse, JobCategoriesResponse, ExperiencesResponse, LocationsResponse, DomainsResponse, TechnologiesResponse, CompanyTypesResponse } from '../../../shared/api'
import type { DeadlineFilter } from '../model/types'

export async function fetchDeadlineJobs(filters?: DeadlineFilter): Promise<JobListResponse> {
  return getJson<JobListResponse>('/api/job_postings/deadline', {
    job_specialty: filters?.job_specialty,
    experience: filters?.experience,
    location: filters?.location,
    domain: filters?.domain,
    technology: filters?.technology,
    company_type: filters?.company_type,
    include_expired: filters?.include_expired,
  })
}

export async function fetchRecentJobs(params?: { exclude_always_recruiting?: boolean }): Promise<JobListResponse> {
  return getJson<JobListResponse>('/api/job_postings/recent', {
    exclude_always_recruiting: params?.exclude_always_recruiting,
  })
}

export async function fetchJobCategories(): Promise<JobCategoriesResponse> {
  return getJson<JobCategoriesResponse>('/api/job_postings/job')
}

export async function fetchExperiences(): Promise<ExperiencesResponse> {
  return getJson<ExperiencesResponse>('/api/job_postings/experience')
}

export async function fetchLocations(): Promise<LocationsResponse> {
  return getJson<LocationsResponse>('/api/job_postings/location')
}

export async function fetchDomains(): Promise<DomainsResponse> {
  return getJson<DomainsResponse>('/api/job_postings/domain')
}

export async function fetchTechnologies(): Promise<TechnologiesResponse> {
  return getJson<TechnologiesResponse>('/api/job_postings/technology')
}

export async function fetchCompanyTypes(): Promise<CompanyTypesResponse> {
  return getJson<CompanyTypesResponse>('/api/job_postings/company_type')
}
