export type ScrapingStatus = { is_scraping: boolean; has_process: boolean }
export type ScrapingRequest = { scraper_type: string; job: string }

export const SCRAPER_TYPES = [
  { value: 'wanted', label: '원티드' },
  { value: 'saramin', label: '사람인' },
  { value: 'jobkorea', label: '잡코리아' },
] as const

export const JOB_OPTIONS = [
  { value: '파이썬 개발자', label: '파이썬 개발자' },
  { value: '머신러닝 엔지니어', label: '머신러닝 엔지니어' },
  { value: '데이터 엔지니어', label: '데이터 엔지니어' },
  { value: '서버 개발자', label: '서버 개발자' },
  { value: '데이터 사이언티스트', label: '데이터 사이언티스트' },
  { value: '빅데이터 엔지니어', label: '빅데이터 엔지니어' },
  { value: '.NET 개발자', label: '.NET 개발자' },
] as const
