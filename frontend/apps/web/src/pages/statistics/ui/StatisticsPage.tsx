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
} from 'recharts'
import {
  useSpecialtyByLocation,
  useExperienceBySpecialty,
  usePostingTrends,
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
    </div>
  )
}
