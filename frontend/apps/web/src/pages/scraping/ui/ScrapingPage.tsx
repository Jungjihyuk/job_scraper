import { useRef, useEffect, useState } from 'react'
import { useDashboardStats } from '../../../entities/dashboard'
import { useScrapingSocket, startScraping, stopScraping, SCRAPER_TYPES, JOB_OPTIONS } from '../../../entities/scraping'
import { LoadingSpinner, ErrorMessage } from '../../../shared/ui'

export function ScrapingPage() {
  const { stats, loading: statsLoading, error: statsError } = useDashboardStats()
  const { messages, isConnected, isScrapingRunning } = useScrapingSocket()
  const [scraperType, setScraperType] = useState<string>(SCRAPER_TYPES[0]?.value ?? 'wanted')
  const [jobOption, setJobOption] = useState<string>(JOB_OPTIONS[0]?.value ?? '파이썬 개발자')
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleStart = async () => {
    try {
      setStatusMessage('스크래핑을 시작합니다...')
      await startScraping({ scraper_type: scraperType, job: jobOption })
    } catch (e) {
      setStatusMessage(e instanceof Error ? e.message : '오류가 발생했습니다')
    }
  }

  const handleStop = async () => {
    try {
      await stopScraping()
      setStatusMessage('스크래핑 중지 요청을 보냈습니다')
    } catch (e) {
      setStatusMessage(e instanceof Error ? e.message : '중지 요청 실패')
    }
  }

  return (
    <div className='space-y-6'>
      {statsLoading && <LoadingSpinner />}
      {statsError && <ErrorMessage message={statsError} />}
      {stats && (
        <div className='grid grid-cols-3 gap-4'>
          <div className='rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm'>
            <div className='text-2xl font-bold text-blue-600'>{stats.total_jobs.toLocaleString()}</div>
            <div className='mt-1 text-sm text-slate-500'>총 채용공고</div>
          </div>
          <div className='rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm'>
            <div className='text-2xl font-bold text-green-600'>{stats.total_companies.toLocaleString()}</div>
            <div className='mt-1 text-sm text-slate-500'>등록된 회사</div>
          </div>
          <div className='rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm'>
            <div className='text-2xl font-bold text-purple-600'>{stats.recent_batches.toLocaleString()}</div>
            <div className='mt-1 text-sm text-slate-500'>최근 스크래핑</div>
          </div>
        </div>
      )}

      <div className='rounded-lg border border-slate-200 bg-white p-6 shadow-sm'>
        <h2 className='text-lg font-semibold text-slate-800'>🚀 스크래핑 실행</h2>
        <div className='mt-4 flex flex-wrap items-center gap-3'>
          <select
            value={scraperType}
            onChange={(e) => setScraperType(e.target.value)}
            className='rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none'
          >
            {SCRAPER_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select
            value={jobOption}
            onChange={(e) => setJobOption(e.target.value)}
            className='rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none'
          >
            {JOB_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          {isScrapingRunning ? (
            <button
              onClick={() => { void handleStop() }}
              className='rounded bg-red-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-600'
            >
              스크래핑 중지
            </button>
          ) : (
            <button
              onClick={() => { void handleStart() }}
              className='rounded bg-blue-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-600'
            >
              스크래핑 시작
            </button>
          )}
          <span className={`text-xs ${isConnected ? 'text-green-500' : 'text-slate-400'}`}>
            {isConnected ? '● 연결됨' : '○ 연결 중...'}
          </span>
        </div>
        {statusMessage && (
          <p className='mt-2 text-sm text-slate-600'>{statusMessage}</p>
        )}
      </div>

      {messages.length > 0 && (
        <div className='rounded-lg border border-slate-200 bg-white p-4 shadow-sm'>
          <h3 className='mb-2 text-sm font-semibold text-slate-700'>📋 실행 로그</h3>
          <div className='h-72 overflow-y-auto rounded bg-slate-50 p-3 font-mono text-xs'>
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`py-0.5 ${msg.type === 'error' ? 'text-red-600' : msg.type === 'complete' ? 'text-green-600' : 'text-slate-700'}`}
              >
                {new Date().toLocaleTimeString()} — {msg.message}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
