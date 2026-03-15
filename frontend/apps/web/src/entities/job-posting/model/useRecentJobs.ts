import { useEffect, useState } from 'react'
import { fetchRecentJobs } from '../api/jobPostingApi'
import type { JobPosting } from '../../../shared/api'

type UseRecentJobsResult = { jobs: JobPosting[]; loading: boolean; error: string | null }

export function useRecentJobs(excludeAlwaysRecruiting: boolean): UseRecentJobsResult {
  const [jobs, setJobs] = useState<JobPosting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchRecentJobs({ exclude_always_recruiting: excludeAlwaysRecruiting })
        setJobs(data.jobs)
      } catch (e) {
        setError(e instanceof Error ? e.message : '알 수 없는 오류')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [excludeAlwaysRecruiting])

  return { jobs, loading, error }
}
