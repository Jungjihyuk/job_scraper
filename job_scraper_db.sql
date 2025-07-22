-- updated_at 자동 업데이트를 위한 트리거 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';


-- 배치 관리 테이블
CREATE TABLE SCRAPING_BATCHES (
  id SERIAL PRIMARY KEY,
  batch_name VARCHAR(255) NOT NULL,
  scraper_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  total_urls INTEGER,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 스크래핑 태스크 테이블
CREATE TABLE SCRAPING_TASKS (
  id SERIAL PRIMARY KEY,
  batch_id INTEGER NOT NULL,
  task_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  url_count INTEGER,
  success_count INTEGER,
  fail_count INTEGER,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER,
  started_at TIMESTAMP,
  duration INTEGER,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 스크래핑된 URL 테이블
CREATE TABLE SCRAPED_URLS (
  id SERIAL PRIMARY KEY,
  batch_id INTEGER NOT NULL,
  url VARCHAR(2048) NOT NULL,
  url_hash VARCHAR(64) UNIQUE NOT NULL,
  status VARCHAR(20) NOT NULL,
  retry_count INTEGER DEFAULT 0,
  error_message TEXT,
  scraped_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 채용공고 테이블
CREATE TABLE JOB_POSTING (
  id SERIAL PRIMARY KEY,
  posting_id VARCHAR(100) UNIQUE NOT NULL,
  job_category_id INTEGER NOT NULL,
  company_id INTEGER NOT NULL,
  location_id INTEGER NOT NULL,
  experience VARCHAR(50),
  position VARCHAR(255),
  position_detail TEXT,
  main_tasks TEXT,
  requirements TEXT,
  preferred TEXT,
  benefits TEXT,
  tags JSONB,
  hiring_process TEXT,
  deadline VARCHAR(50),
  posted_date TIMESTAMP
);

-- 회사 정보 테이블
CREATE TABLE COMPANIES (
  company_id SERIAL PRIMARY KEY,
  company_name VARCHAR(255) NOT NULL,
  company_size VARCHAR(50),
  is_listed BOOLEAN,
  listing_market VARCHAR(20),
  stock_code VARCHAR(20),
  blind_registered BOOLEAN,
  blind_avg_rating NUMERIC(2,1),
  blind_career_rating NUMERIC(2,1),
  blind_worklife_rating NUMERIC(2,1),
  blind_welfare_rating NUMERIC(2,1),
  blind_culture_rating NUMERIC(2,1),
  blind_management_rating NUMERIC(2,1),
  blind_last_updated TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 직무 카테고리 테이블
CREATE TABLE JOB_CATEGORIES (
  job_category_id SERIAL PRIMARY KEY,
  job_category VARCHAR(100) NOT NULL,
  job_field VARCHAR(100) NOT NULL,
  job_specialty VARCHAR(100),
  scraper_type VARCHAR(50) NOT NULL
);

-- 지역 정보 테이블
CREATE TABLE LOCATIONS (
  location_id SERIAL PRIMARY KEY,
  location VARCHAR(100) NOT NULL,
  location_detail VARCHAR(255)
);

-- 성능 최적화 인덱스 생성
CREATE UNIQUE INDEX unique_job_combination ON JOB_CATEGORIES (job_category, job_field, COALESCE(job_specialty, ''));
CREATE INDEX idx_job_posting_company ON JOB_POSTING (company_id);
CREATE INDEX idx_job_posting_location ON JOB_POSTING (location_id);
CREATE INDEX idx_job_posting_category ON JOB_POSTING (job_category_id);
CREATE INDEX idx_job_posting_posted_date ON JOB_POSTING (posted_date DESC);
CREATE INDEX idx_scraped_urls_batch ON SCRAPED_URLS (batch_id);
CREATE INDEX idx_scraped_urls_status ON SCRAPED_URLS (status);
CREATE INDEX idx_scraped_urls_hash ON SCRAPED_URLS (url_hash);
CREATE INDEX idx_scraping_tasks_batch ON SCRAPING_TASKS (batch_id);
CREATE INDEX idx_scraping_batches_status ON SCRAPING_BATCHES (status);
CREATE INDEX idx_scraping_batches_type ON SCRAPING_BATCHES (scraper_type);
CREATE INDEX idx_companies_name ON COMPANIES (company_name);
CREATE INDEX idx_companies_listing ON COMPANIES (is_listed, listing_market);

-- 외래 키 제약 조건
ALTER TABLE SCRAPING_TASKS ADD CONSTRAINT fk_scraping_tasks_batch 
  FOREIGN KEY (batch_id) REFERENCES SCRAPING_BATCHES (id) ON DELETE CASCADE;

ALTER TABLE SCRAPED_URLS ADD CONSTRAINT fk_scraped_urls_batch 
  FOREIGN KEY (batch_id) REFERENCES SCRAPING_BATCHES (id) ON DELETE CASCADE;

ALTER TABLE JOB_POSTING ADD CONSTRAINT fk_job_posting_company 
  FOREIGN KEY (company_id) REFERENCES COMPANIES (company_id) 
  ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE JOB_POSTING ADD CONSTRAINT fk_job_posting_location 
  FOREIGN KEY (location_id) REFERENCES LOCATIONS (location_id)
  ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE JOB_POSTING ADD CONSTRAINT fk_job_posting_category 
  FOREIGN KEY (job_category_id) REFERENCES JOB_CATEGORIES (job_category_id)
  ON DELETE RESTRICT ON UPDATE CASCADE;

-- 각 테이블에 updated_at 자동 업데이트 트리거 생성
CREATE TRIGGER update_scraping_batches_updated_at 
  BEFORE UPDATE ON SCRAPING_BATCHES 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scraping_tasks_updated_at 
  BEFORE UPDATE ON SCRAPING_TASKS 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scraped_urls_updated_at 
  BEFORE UPDATE ON SCRAPED_URLS 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at 
  BEFORE UPDATE ON COMPANIES 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 컬럼 코멘트 추가
COMMENT ON COLUMN SCRAPING_BATCHES.scraper_type IS 'wanted/saramin/jobkorea';
COMMENT ON COLUMN SCRAPING_BATCHES.status IS 'pending/running/completed/failed';
COMMENT ON COLUMN SCRAPING_BATCHES.started_at IS '스크래핑 시작 시간';

COMMENT ON COLUMN SCRAPING_TASKS.task_type IS 'url_collector/url_validator/content_scraper/db_saver/total';
COMMENT ON COLUMN SCRAPING_TASKS.status IS 'pending/running/completed/failed';
COMMENT ON COLUMN SCRAPING_TASKS.duration IS '단위: second';

COMMENT ON COLUMN JOB_POSTING.position IS '직무명';
COMMENT ON COLUMN JOB_POSTING.position_detail IS '포지션 상세';

COMMENT ON COLUMN COMPANIES.company_size IS 'NULL 허용, 추후 업데이트 | 대기업/중견기업/중소기업/스타트업';
COMMENT ON COLUMN COMPANIES.is_listed IS '상장 여부';
COMMENT ON COLUMN COMPANIES.listing_market IS 'KOSPI/KOSDAQ';
COMMENT ON COLUMN COMPANIES.stock_code IS '종목 코드';
COMMENT ON COLUMN COMPANIES.blind_registered IS '블라인드 등록 여부';

COMMENT ON COLUMN JOB_CATEGORIES.scraper_type IS 'wanted/saramin/jobkorea';

COMMENT ON COLUMN LOCATIONS.location IS '근무 지역';
COMMENT ON COLUMN LOCATIONS.location_detail IS '근무 지역 상세 주소';