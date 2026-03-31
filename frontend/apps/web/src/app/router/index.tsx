import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '../../widgets/layout'
import { LoadingSpinner } from '../../shared/ui'

const ScrapingPage = lazy(() =>
  import('../../pages/scraping').then((m) => ({ default: m.ScrapingPage })),
)
const DeadlinePage = lazy(() =>
  import('../../pages/deadline').then((m) => ({ default: m.DeadlinePage })),
)
const RecentPage = lazy(() =>
  import('../../pages/recent').then((m) => ({ default: m.RecentPage })),
)
const StatisticsPage = lazy(() =>
  import('../../pages/statistics').then((m) => ({ default: m.StatisticsPage })),
)

export function AppRouter() {
  return (
    <Layout>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path='/' element={<Navigate to='/scraping' replace />} />
          <Route path='/scraping' element={<ScrapingPage />} />
          <Route path='/deadline' element={<DeadlinePage />} />
          <Route path='/recent' element={<RecentPage />} />
          <Route path='/statistics' element={<StatisticsPage />} />
          <Route path='*' element={<Navigate to='/scraping' replace />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
