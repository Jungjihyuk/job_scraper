import { useEffect, useState } from 'react'
import { fetchDeadlineJobs } from '../api/jobPostingApi'
import type { JobPosting } from '../../../shared/api'
import type { DeadlineFilter } from './types'

type UseDeadlineJobsResult = { jobs: JobPosting[]; loading: boolean; error: string | null }

export function useDeadlineJobs(filters?: DeadlineFilter): UseDeadlineJobsResult {
  const [jobs, setJobs] = useState<JobPosting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchDeadlineJobs(filters)
        setJobs(data.jobs)
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [filters?.job_specialty, filters?.experience, filters?.location, filters?.include_expired])

  return { jobs, loading, error }
}
