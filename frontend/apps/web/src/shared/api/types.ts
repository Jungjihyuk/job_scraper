export type ApiError = { message: string; status?: number }

export type WsStatusEvent = { type: 'status'; message: string; progress: number }
export type WsLogEvent = { type: 'log'; message: string }
export type WsCompleteEvent = { type: 'complete'; message: string; progress: number }
export type WsErrorEvent = { type: 'error'; message: string }
export type WsStoppedEvent = { type: 'stopped'; message: string }
export type WsEvent =
  | WsStatusEvent
  | WsLogEvent
  | WsCompleteEvent
  | WsErrorEvent
  | WsStoppedEvent

export type DashboardStats = {
  total_jobs: number
  total_companies: number
  recent_batches: number
}

export type JobPosting = {
  position: string
  job_specialty: string
  company_name: string
  company_type?: string | null
  location: string
  experience: string
  deadline: string | null
  is_always_recruiting: boolean
  original_url: string | null
  tags: string[] | null
  posted_date?: string | null
  domain_l1?: string | null
  domain_l2?: string | null
  core_technologies?: string[] | null
}

export type JobListResponse = { jobs: JobPosting[] }
export type JobCategoriesResponse = { categories: string[] }
export type ExperiencesResponse = { experiences: string[] }
export type LocationsResponse = { locations: string[] }
export type ScrapingStatusResponse = { is_scraping: boolean; has_process: boolean }

export type ChartDataset = {
  label: string
  data: number[]
  backgroundColor?: string
  borderColor?: string
  fill?: boolean
  tension?: number
}

export type ChartResponse = { labels: string[]; datasets: ChartDataset[] }
export type AvailableYearsResponse = { years: number[] }
export type DomainsResponse = { domains: string[] }
export type TechnologiesResponse = { technologies: string[] }
export type AvailableTechnologiesResponse = { technologies: string[] }
