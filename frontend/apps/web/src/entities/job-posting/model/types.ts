export type { JobPosting, JobListResponse, JobCategoriesResponse, ExperiencesResponse, LocationsResponse } from '../../../shared/api'

export type DeadlineFilter = {
  job_specialty?: string
  experience?: string
  location?: string
  domain?: string
  technology?: string
  include_expired?: boolean
}
