import { useState } from 'react'
import { useDeadlineJobs, useFilterOptions, JobCard } from '../../../entities/job-posting'
import type { DeadlineFilter } from '../../../entities/job-posting'
import { LoadingSpinner, ErrorMessage, EmptyState } from '../../../shared/ui'

export function DeadlinePage() {
  const [pendingFilters, setPendingFilters] = useState<DeadlineFilter>({
    job_specialty: '',
    experience: '',
    location: '',
    domain: '',
    technology: '',
    company_type: '',
    include_expired: false,
  })
  const [appliedFilters, setAppliedFilters] = useState<DeadlineFilter>({})

  const { jobs, loading, error } = useDeadlineJobs(appliedFilters)
  const { categories, experiences, locations, domains, technologies, companyTypes, loading: optionsLoading } = useFilterOptions()

  const applyFilters = () => {
    setAppliedFilters({
      job_specialty: pendingFilters.job_specialty || undefined,
      experience: pendingFilters.experience || undefined,
      location: pendingFilters.location || undefined,
      domain: pendingFilters.domain || undefined,
      technology: pendingFilters.technology || undefined,
      company_type: pendingFilters.company_type || undefined,
      include_expired: pendingFilters.include_expired,
    })
  }

  return (
    <div className='space-y-6'>
      <h2 className='text-xl font-bold text-slate-800'>⏰ 마감일 임박 채용공고</h2>

      <div className='rounded-lg border border-slate-200 bg-white p-4 shadow-sm'>
        <div className='flex flex-wrap items-center gap-3'>
          <div className='flex items-center gap-2'>
            <label className='text-sm font-medium text-slate-600'>직무</label>
            <select
              value={pendingFilters.job_specialty ?? ''}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, job_specialty: e.target.value }))}
              disabled={optionsLoading}
              className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
            >
              <option value=''>전체</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
          <div className='flex items-center gap-2'>
            <label className='text-sm font-medium text-slate-600'>경력</label>
            <select
              value={pendingFilters.experience ?? ''}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, experience: e.target.value }))}
              disabled={optionsLoading}
              className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
            >
              <option value=''>전체</option>
              {experiences.map((exp) => (
                <option key={exp} value={exp}>{exp}</option>
              ))}
            </select>
          </div>
          <div className='flex items-center gap-2'>
            <label className='text-sm font-medium text-slate-600'>지역</label>
            <select
              value={pendingFilters.location ?? ''}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, location: e.target.value }))}
              disabled={optionsLoading}
              className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
            >
              <option value=''>전체</option>
              {locations.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>
          <div className='flex items-center gap-2'>
            <label className='text-sm font-medium text-slate-600'>도메인</label>
            <select
              value={pendingFilters.domain ?? ''}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, domain: e.target.value }))}
              disabled={optionsLoading}
              className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
            >
              <option value=''>전체</option>
              {domains.map((dom) => (
                <option key={dom} value={dom}>{dom}</option>
              ))}
            </select>
          </div>
          <div className='flex items-center gap-2'>
            <label className='text-sm font-medium text-slate-600'>기술</label>
            <select
              value={pendingFilters.technology ?? ''}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, technology: e.target.value }))}
              disabled={optionsLoading}
              className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
            >
              <option value=''>전체</option>
              {technologies.map((tech) => (
                <option key={tech} value={tech}>{tech}</option>
              ))}
            </select>
          </div>
          <div className='flex items-center gap-2'>
            <label className='text-sm font-medium text-slate-600'>기업유형</label>
            <select
              value={pendingFilters.company_type ?? ''}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, company_type: e.target.value }))}
              disabled={optionsLoading}
              className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
            >
              <option value=''>전체</option>
              {companyTypes.map((ct) => (
                <option key={ct} value={ct}>{ct}</option>
              ))}
            </select>
          </div>
          <label className='flex items-center gap-1.5 text-sm text-slate-600'>
            <input
              type='checkbox'
              checked={!(pendingFilters.include_expired ?? false)}
              onChange={(e) => setPendingFilters((prev) => ({ ...prev, include_expired: !e.target.checked }))}
              className='rounded'
            />
            마감된 공고 제외
          </label>
          <button
            onClick={applyFilters}
            className='rounded bg-blue-500 px-3 py-1 text-sm font-medium text-white hover:bg-blue-600'
          >
            조회
          </button>
        </div>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} />}
      {!loading && !error && jobs.length === 0 && (
        <EmptyState message='조건에 맞는 채용공고가 없습니다.' icon='🔍' />
      )}
      {!loading && !error && jobs.length > 0 && (
        <div className='space-y-3'>
          {jobs.map((job, i) => (
            <JobCard key={`${job.company_name}-${job.position}-${i}`} job={job} />
          ))}
        </div>
      )}
    </div>
  )
}
