import { getJson } from '../../../shared/api'
import type { JobListResponse, JobCategoriesResponse, ExperiencesResponse, LocationsResponse } from '../../../shared/api'
import type { DeadlineFilter } from '../model/types'

export async function fetchDeadlineJobs(filters?: DeadlineFilter): Promise<JobListResponse> {
  return getJson<JobListResponse>('/api/job_postings/deadline', {
    job_specialty: filters?.job_specialty,
    experience: filters?.experience,
    location: filters?.location,
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
