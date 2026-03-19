import type { JobPosting } from '../../../shared/api'

type Props = { job: JobPosting }

function getDaysLeft(deadline: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const deadlineDate = new Date(deadline)
  deadlineDate.setHours(0, 0, 0, 0)
  return Math.ceil((deadlineDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function DeadlineBadge({ job }: { job: JobPosting }) {
  if (job.is_always_recruiting) {
    return <span className='rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700'>🔄 상시채용</span>
  }
  if (!job.deadline) return null
  const days = getDaysLeft(job.deadline)
  if (days < 0) return <span className='rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500'>❌ 마감</span>
  if (days <= 3) return <span className='rounded bg-red-100 px-2 py-0.5 text-xs text-red-700'>🔥 D-{days}</span>
  if (days <= 7) return <span className='rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700'>⚠️ D-{days}</span>
  return <span className='rounded bg-green-100 px-2 py-0.5 text-xs text-green-700'>🟢 D-{days}</span>
}

export function JobCard({ job }: Props) {
  const tags = Array.isArray(job.tags) ? job.tags : job.tags ? [job.tags] : []
  const techs = Array.isArray(job.core_technologies) ? job.core_technologies : []

  return (
    <div className='rounded-lg border border-slate-200 bg-white p-4 shadow-sm'>
      <div className='text-base font-semibold text-slate-800'>
        {job.original_url ? (
          <a
            href={job.original_url}
            target='_blank'
            rel='noopener noreferrer'
            className='hover:text-blue-600 hover:underline'
          >
            {job.position || '미상'}
          </a>
        ) : (
          job.position || '미상'
        )}
      </div>
      <div className='mt-2 flex flex-wrap gap-2 text-sm text-slate-600'>
        <span>🏢 {job.company_name || '미상'}</span>
        <span>📍 {job.location || '미상'}</span>
        <span>🎯 {job.job_specialty || '미분류'}</span>
        <span>👥 {job.experience || '미상'}</span>
        <DeadlineBadge job={job} />
      </div>
      {job.domain && (
        <div className='mt-2'>
          <span className='rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700'>
            {job.domain}
          </span>
        </div>
      )}
      {techs.length > 0 && (
        <div className='mt-2 flex flex-wrap gap-1'>
          {techs.map((tech, i) => (
            <span key={i} className='rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700'>
              {tech}
            </span>
          ))}
        </div>
      )}
      {tags.length > 0 && (
        <div className='mt-2 flex flex-wrap gap-1'>
          {tags.map((tag, i) => (
            <span key={i} className='rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600'>
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
