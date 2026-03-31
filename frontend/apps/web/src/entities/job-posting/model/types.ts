export type { JobPosting, JobListResponse, JobCategoriesResponse, ExperiencesResponse, LocationsResponse } from '../../../shared/api'

export type DeadlineFilter = {
  specialty_l1?: string
  specialty_l2?: string
  employment_type?: string
  experience?: string
  location?: string
  domain?: string
  technology?: string
  company_type?: string
  include_expired?: boolean
}
