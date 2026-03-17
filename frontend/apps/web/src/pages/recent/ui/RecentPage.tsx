import { useState } from 'react'
import { useRecentJobs, JobCard } from '../../../entities/job-posting'
import { LoadingSpinner, ErrorMessage, EmptyState } from '../../../shared/ui'

const PAGE_SIZE = 10

export function RecentPage() {
  const [excludeAlwaysRecruiting, setExcludeAlwaysRecruiting] = useState(false)
  const [limit, setLimit] = useState(PAGE_SIZE)
  const { jobs, loading, error } = useRecentJobs(excludeAlwaysRecruiting)

  const visibleJobs = jobs.slice(0, limit)
  const hasMore = jobs.length > limit

  const handleRefresh = () => {
    setLimit(PAGE_SIZE)
  }

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h2 className='text-xl font-bold text-slate-800'>📄 최근 등록된 채용공고</h2>
        <div className='flex items-center gap-4'>
          <label className='flex items-center gap-1.5 text-sm text-slate-600'>
            <input
              type='checkbox'
              checked={excludeAlwaysRecruiting}
              onChange={(e) => {
                setExcludeAlwaysRecruiting(e.target.checked)
                setLimit(PAGE_SIZE)
              }}
              className='rounded'
            />
            상시채용 제외
          </label>
          <button
            onClick={handleRefresh}
            className='rounded border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-50'
          >
            새로고침
          </button>
        </div>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} />}
      {!loading && !error && jobs.length === 0 && (
        <EmptyState message='채용공고가 없습니다.' icon='📭' />
      )}
      {!loading && !error && visibleJobs.length > 0 && (
        <>
          <div className='space-y-3'>
            {visibleJobs.map((job, i) => (
              <JobCard key={`${job.company_name}-${job.position}-${i}`} job={job} />
            ))}
          </div>
          {hasMore && (
            <div className='flex justify-center'>
              <button
                onClick={() => setLimit((prev) => prev + PAGE_SIZE)}
                className='rounded border border-slate-300 px-6 py-2 text-sm text-slate-600 hover:bg-slate-50'
              >
                더 보기
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
