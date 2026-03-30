import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer,
  LineChart,
  Line,
  Treemap,
} from 'recharts'
import {
  useSpecialtyByLocation,
  useExperienceBySpecialty,
  usePostingTrends,
  useDomainDistribution,
  useCompanyTypeDistribution,
  useDomainByCompanyType,
  useTechnologyByCompanyType,
  useTechnologyTrends,
} from '../../../entities/statistics'
import type { StackedBarData } from '../../../entities/statistics'
import { useFilterOptions } from '../../../entities/job-posting'
import { LoadingSpinner, ErrorMessage, EmptyState } from '../../../shared/ui'

const COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#14b8a6', '#ec4899', '#84cc16',
]

function getBarKeys(data: StackedBarData): string[] {
  if (data.length === 0) return []
  return Object.keys(data[0] ?? {}).filter((k) => k !== 'name')
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function TreemapCell(props: any) {
  const { x = 0, y = 0, width = 0, height = 0, depth, root } = props
  // 데이터 원본에서 직접 가져옴 (Recharts가 spread 해줌)
  const dataFill: string | undefined = props.fill
  const name: string = props.name ?? ''
  const size: number = props.size ?? 0
  const groupName: string = props.groupName ?? root?.name ?? ''

  if (width < 2 || height < 2) return null

  if (depth === 1) {
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} fill={dataFill ?? '#94a3b8'} stroke='#fff' strokeWidth={3} rx={4} opacity={0.25} />
        {width > 50 && height > 20 && (
          <text x={x + 8} y={y + 16} fontSize={13} fill='#334155' fontWeight={700}>
            {name}
          </text>
        )}
      </g>
    )
  }

  // depth 2 = 도메인 리프
  const cellFill = dataFill ?? '#94a3b8'
  const fontSize = width < 40 || height < 20 ? 9 : 11
  const showName = width > 28 && height > 14
  const showCount = width > 35 && height > 28

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={cellFill} stroke='#fff' strokeWidth={1.5} rx={3} />
      {showName && (
        <text
          x={x + width / 2}
          y={y + height / 2 + (showCount ? -6 : 0)}
          textAnchor='middle'
          dominantBaseline='central'
          fontSize={fontSize}
          fill='#fff'
          fontWeight={600}
        >
          {width < 60 && name.length > 6 ? name.slice(0, 5) + '…' : name}
        </text>
      )}
      {showCount && (
        <text x={x + width / 2} y={y + height / 2 + 10} textAnchor='middle' dominantBaseline='central' fontSize={9} fill='#fff' opacity={0.8}>
          {size}건
        </text>
      )}
    </g>
  )
}
/* eslint-enable @typescript-eslint/no-explicit-any */

function TreemapTooltip({ active, payload }: { active?: boolean; payload?: any[] }) {
  if (!active || !payload || payload.length === 0) return null
  const item = payload[0]?.payload
  if (!item || item.depth === 1) return null
  return (
    <div className='rounded border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg'>
      <p className='font-semibold text-slate-700'>{item.groupName || item.root?.name || '—'}</p>
      <p className='text-slate-600'>{item.name}</p>
      <p className='font-medium text-slate-800'>{item.size?.toLocaleString()}건</p>
    </div>
  )
}

export function StatisticsPage() {
  const { data: specialtyData, loading: l1, error: e1 } = useSpecialtyByLocation()
  const { data: experienceData, loading: l2, error: e2 } = useExperienceBySpecialty()
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>('')
  const [selectedYear, setSelectedYear] = useState<number | undefined>()
  const {
    data: trendData,
    years,
    loading: l3,
    error: e3,
  } = usePostingTrends(selectedSpecialty || undefined, selectedYear)
  const { categories } = useFilterOptions()

  // Domain distribution
  const { data: domainData, loading: l4, error: e4 } = useDomainDistribution()

  // Company type distribution
  const { data: companyTypeData, loading: l6, error: e6 } = useCompanyTypeDistribution()

  // Domain by company type
  const { data: domainByCtData, loading: l7, error: e7 } = useDomainByCompanyType()

  // Technology by company type (100% horizontal bar)
  const { data: techByCtData, loading: l8, error: e8 } = useTechnologyByCompanyType()

  // Technology trends
  const [selectedTech, setSelectedTech] = useState<string>('')
  const [selectedTechYear, setSelectedTechYear] = useState<number | undefined>()
  const {
    data: techTrendData,
    technologies: availableTechs,
    loading: l5,
    error: e5,
  } = useTechnologyTrends(selectedTech || undefined, selectedTechYear)

  return (
    <div className='space-y-10'>
      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>📊 지역별 직무 분포</h2>
        {l1 && <LoadingSpinner />}
        {e1 && <ErrorMessage message={e1} />}
        {!l1 && !e1 && specialtyData.length === 0 && <EmptyState message='데이터가 없습니다.' />}
        {!l1 && !e1 && specialtyData.length > 0 && (
          <ResponsiveContainer width='100%' height={350}>
            <BarChart data={specialtyData}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='name' />
              <YAxis />
              <Tooltip />
              <Legend />
              {getBarKeys(specialtyData).map((key, i) => (
                <Bar key={key} dataKey={key} stackId='a' fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>📊 직무별 경력 분포</h2>
        {l2 && <LoadingSpinner />}
        {e2 && <ErrorMessage message={e2} />}
        {!l2 && !e2 && experienceData.length === 0 && <EmptyState message='데이터가 없습니다.' />}
        {!l2 && !e2 && experienceData.length > 0 && (
          <ResponsiveContainer width='100%' height={400}>
            <BarChart data={experienceData} layout='vertical'>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis type='number' unit='%' />
              <YAxis dataKey='name' type='category' width={120} />
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
              <Legend />
              {getBarKeys(experienceData).map((key, i) => (
                <Bar key={key} dataKey={key} stackId='a' fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>📈 채용 공고 추이</h2>
        <div className='mb-4 flex flex-wrap gap-3'>
          <select
            value={selectedYear ?? ''}
            onChange={(e) => setSelectedYear(e.target.value ? Number(e.target.value) : undefined)}
            className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
          >
            <option value=''>전체 연도</option>
            {years.map((y) => (
              <option key={y} value={y}>{y}년</option>
            ))}
          </select>
          <select
            value={selectedSpecialty}
            onChange={(e) => setSelectedSpecialty(e.target.value)}
            className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
          >
            <option value=''>전체 직무</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
        {l3 && <LoadingSpinner />}
        {e3 && <ErrorMessage message={e3} />}
        {!l3 && !e3 && trendData.length === 0 && <EmptyState message='데이터가 없습니다.' />}
        {!l3 && !e3 && trendData.length > 0 && (
          <ResponsiveContainer width='100%' height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='date' />
              <YAxis />
              <Tooltip />
              <Line type='monotone' dataKey='count' stroke='#6366f1' dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>🏷️ 도메인 분포</h2>
        {l4 && <LoadingSpinner />}
        {e4 && <ErrorMessage message={e4} />}
        {!l4 && !e4 && domainData.length === 0 && <EmptyState message='도메인 데이터가 없습니다.' />}
        {!l4 && !e4 && domainData.length > 0 && (
          <ResponsiveContainer width='100%' height={350}>
            <BarChart data={domainData}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='name' />
              <YAxis />
              <Tooltip />
              <Legend />
              {getBarKeys(domainData).map((key, i) => (
                <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>🏢 기업 유형별 공고 분포</h2>
        {l6 && <LoadingSpinner />}
        {e6 && <ErrorMessage message={e6} />}
        {!l6 && !e6 && companyTypeData.length === 0 && <EmptyState message='기업 유형 데이터가 없습니다.' />}
        {!l6 && !e6 && companyTypeData.length > 0 && (
          <ResponsiveContainer width='100%' height={350}>
            <BarChart data={companyTypeData}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='name' />
              <YAxis />
              <Tooltip />
              <Legend />
              {getBarKeys(companyTypeData).map((key, i) => (
                <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>🏢 기업 유형별 도메인 분포</h2>
        {l7 && <LoadingSpinner />}
        {e7 && <ErrorMessage message={e7} />}
        {!l7 && !e7 && domainByCtData.length === 0 && <EmptyState message='데이터가 없습니다.' />}
        {!l7 && !e7 && domainByCtData.length > 0 && (
          <ResponsiveContainer width='100%' height={450}>
            <Treemap
              data={domainByCtData}
              dataKey='size'
              aspectRatio={4 / 3}
              stroke='#fff'
              content={<TreemapCell />}
            >
              <Tooltip content={<TreemapTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>🏢 기업 유형별 기술 스택 비율</h2>
        <p className='mb-3 text-sm text-slate-500'>상위 10개 기술 · 기업유형별 100% 비율 비교</p>
        {l8 && <LoadingSpinner />}
        {e8 && <ErrorMessage message={e8} />}
        {!l8 && !e8 && techByCtData.length === 0 && <EmptyState message='데이터가 없습니다.' />}
        {!l8 && !e8 && techByCtData.length > 0 && (
          <ResponsiveContainer width='100%' height={Math.max(techByCtData.length * 50, 300)}>
            <BarChart data={techByCtData} layout='vertical'>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis type='number' unit='%' domain={[0, 100]} />
              <YAxis dataKey='name' type='category' width={90} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
              <Legend />
              {getBarKeys(techByCtData).map((key, i) => (
                <Bar key={key} dataKey={key} stackId='a' fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <hr className='border-slate-200' />

      <section>
        <h2 className='mb-4 text-xl font-bold text-slate-800'>🔧 기술 트렌드</h2>
        <div className='mb-4 flex flex-wrap gap-3'>
          <select
            value={selectedTechYear ?? ''}
            onChange={(e) => setSelectedTechYear(e.target.value ? Number(e.target.value) : undefined)}
            className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
          >
            <option value=''>전체 연도</option>
            {years.map((y) => (
              <option key={y} value={y}>{y}년</option>
            ))}
          </select>
          <select
            value={selectedTech}
            onChange={(e) => setSelectedTech(e.target.value)}
            className='rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none'
          >
            <option value=''>전체 기술</option>
            {availableTechs.map((tech) => (
              <option key={tech} value={tech}>{tech}</option>
            ))}
          </select>
        </div>
        {l5 && <LoadingSpinner />}
        {e5 && <ErrorMessage message={e5} />}
        {!l5 && !e5 && techTrendData.length === 0 && <EmptyState message='기술 트렌드 데이터가 없습니다.' />}
        {!l5 && !e5 && techTrendData.length > 0 && (
          <ResponsiveContainer width='100%' height={350}>
            <LineChart data={techTrendData}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='date' />
              <YAxis />
              <Tooltip />
              <Legend />
              {selectedTech ? (
                <Line type='monotone' dataKey='count' stroke='#6366f1' dot={false} />
              ) : (
                availableTechs.slice(0, 10).map((tech, i) => (
                  <Line key={tech} type='monotone' dataKey={tech} stroke={COLORS[i % COLORS.length]} dot={false} />
                ))
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>
    </div>
  )
}
