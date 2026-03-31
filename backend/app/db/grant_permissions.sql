-- 데이터베이스 생성 
CREATE DATABASE job_scraper_db;

-- 데이터베이스 접근 권한 부여
GRANT CONNECT ON DATABASE job_scraper_db TO jihyeok;

-- 스키마 사용 권한 부여
GRANT USAGE, CREATE ON SCHEMA public TO jihyeok;

-- 데이터베이스 소유자 변경
ALTER DATABASE job_scraper_db OWNER TO jihyeok;
