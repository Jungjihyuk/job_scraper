export type ScrapingStatus = { is_scraping: boolean; has_process: boolean }
export type ScrapingRequest = { scraper_type: string; job: string; scrape_mode: string }

export const SCRAPE_MODES = [
  { value: 'default', label: '기본', description: '설정된 횟수만큼 스크롤' },
  { value: 'incremental', label: '증분 수집', description: '신규 공고가 없으면 조기 종료' },
  { value: 'full', label: '전체 수집', description: '페이지 끝까지 스크롤' },
] as const

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
  { value: '프론트엔드 개발자', label: '프론트엔드 개발자'},
  { value: '.NET 개발자', label: '.NET 개발자' },
] as const
