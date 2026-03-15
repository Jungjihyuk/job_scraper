import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

type Props = { children: ReactNode }

const navItems = [
  { to: '/scraping', label: '🔍 스크래핑 관리' },
  { to: '/deadline', label: '⏰ 마감일 순 조회' },
  { to: '/recent', label: '📄 최근등록 공고' },
  { to: '/statistics', label: '📊 통계분석' },
]

export function Layout({ children }: Props) {
  return (
    <div className='min-h-screen bg-slate-50'>
      <header className='bg-white shadow-sm'>
        <div className='mx-auto max-w-7xl px-4'>
          <div className='py-4'>
            <h1 className='text-xl font-bold text-slate-800'>🎯 Job Scraper Dashboard</h1>
            <p className='text-sm text-slate-500'>채용공고 스크래핑 대시보드</p>
          </div>
          <nav className='flex gap-1 pb-0'>
            {navItems.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `rounded-t-lg px-4 py-2 text-sm font-medium transition-colors ${
                    isActive ? 'bg-blue-500 text-white' : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className='mx-auto max-w-7xl px-4 py-6'>{children}</main>
    </div>
  )
}
