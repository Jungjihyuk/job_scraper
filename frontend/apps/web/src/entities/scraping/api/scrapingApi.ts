import { getJson, postJson } from '../../../shared/api'
import type { ScrapingRequest, ScrapingStatus } from '../model/types'

export async function fetchScrapingStatus(): Promise<ScrapingStatus> {
  return getJson<ScrapingStatus>('/api/scraping/status')
}

export async function startScraping(request: ScrapingRequest): Promise<{ message: string }> {
  return postJson<{ message: string }>('/api/scraping/start', request)
}

export async function stopScraping(): Promise<{ message: string }> {
  return postJson<{ message: string }>('/api/scraping/stop', {})
}
