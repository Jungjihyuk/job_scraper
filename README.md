# <div align="center">Job Scraper</div>

채용 트렌드 분석과 맞춤형 채용공고 추천을 위한 구직공고 스크래핑 시스템

## <div align="center">프로젝트 개요</div>
> 이 스크래핑 시스템은 급변하는 `채용 시장`의 현실을 빠르게 파악하고 사용자에게 빠르게 `맞춤 공고`를 제안하는 것을 목표로 합니다. 
> 가능한 `많은 채용 사이트`로 부터 채용 공고를 수집하고 데이터를 기반으로 구직 결정을 빠르게 결정하는데 도움을 줄 수 있습니다.

## <div align="center">주요 기능</div>

### 핵심 컴포넌트

- **Pipeline System**: 병렬 데이터 수집 파이프라인
- **Web Dashboard**: FastAPI 기반 웹 인터페이스
- **Database Layer**: PostgreSQL 기반 데이터 저장
- **Scraper Engine**: 동적 콘텐츠 스크래핑 엔진

### 파이프라인 단계

1. **URL Collector**: 구인구직 사이트 채용 공고 URL 수집
2. **URL Validator**: 수집된 URL의 유효성 검증
3. **Content Scraper**: 각 사이트별 콘텐츠 추출 및 파싱
4. **Database Saver**: 정제된 데이터를 데이터베이스에 저장

## <div align="center">주요 기능 세부사항</div>

### 데이터 수집
- **동적 콘텐츠 처리**: 무한 스크롤, JavaScript 렌더링, 데이터 지연로딩 지원
- **지능형 스크래핑**: 각 사이트의 구조 변화 대응 (Playwright/Selenium)
- **중복 방지**: URL 중복 및 내용 데이터 중복 처리
- **에러 복구**: 네트워크 데이터 재시도 메커니즘

### 웹 대시보드
- **실시간 모니터링**: WebSocket 기반 스크래핑 진행 상황 모니터링
- **데이터 시각화**: 수집 사이트별 통계 및 분석
- **스크래핑 관리**: 각 웹사이트별 개별 스크래핑 시작/중단
- **API 인터페이스**: RESTful API를 통한 데이터 접근

### 데이터베이스 구조
- **배치 관리**: 실행 날짜, 상태 정보, 파이프라인 설정 저장
- **사이트 정보**: 회사명, 업종, 위치, 급여 정보등 저장
- **스크래핑 상태데이터**: 에러 정보, 처리 통계, 성능 메트릭 저장

## <div align="center">기술 스택 및 의존성</div>

### 백엔드
- **Python 3.10+**
- **FastAPI**: 웹 API 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 연동 도구
- **PostgreSQL**: 메인 데이터베이스
- **asyncio**: 비동기 처리

### 스크래핑
- **BeautifulSoup4**: HTML 파싱
- **Selenium**: 동적 사이트 자동화
- **Playwright**: 고성능 브라우저 자동화 도구
- **requests/httpx**: HTTP 클라이언트

### 코드 품질 도구
- **Black**: 코드 포매팅
- **isort**: import 정렬
- **flake8**: 코드 품질 검사

## <div align="center">프로젝트 구조</div>

```
job_scraper/
├── job_scraper/
│   ├── config/                 # 설정 파일들
│   │   ├── logging_config.py   # 로깅 설정
│   │   └── settings.py         # 애플리케이션 설정
│   ├── database/               # 데이터베이스 레이어
│   │   ├── models.py           # SQLAlchemy 모델
│   │   ├── connection.py       # DB 연결 관리
│   │   └── config.py           # DB 설정
│   ├── pipeline/               # 데이터 수집 파이프라인
│   │   ├── core/               # 핵심 파이프라인 컴포넌트
│   │   │   ├── base_stage.py   # 파이프라인 스테이지 베이스 클래스
│   │   │   ├── pipeline_manager.py  # 파이프라인 매니저
│   │   │   └── data_models.py  # 데이터 모델
│   │   └── stages/             # 파이프라인 스테이지들
│   │       ├── url_collector.py    # URL 수집기
│   │       ├── url_validator.py    # URL 검증기
│   │       ├── content_scraper.py  # 사이트 콘텐츠 스크래핑
│   │       └── database_saver.py   # DB 저장
│   ├── scrapers/               # 스크래핑 엔진
│   │   ├── wanted_scraper.py   # 원티드 스크래퍼
│   │   └── scraper_manager.py  # 스크래퍼 매니저
│   ├── web_dashboard/          # 웹 대시보드
│   │   ├── api/v1/            # API 인터페이스
│   │   ├── schemas/           # Pydantic 스키마
│   │   ├── templates/         # HTML 템플릿
│   │   └── static/           # 정적 파일
│   ├── utils/                 # 유틸리티
│   ├── main_pipeline.py       # 파이프라인 실행
│   └── main.py               # cli 스크래핑 실행
├── tests/                    # 테스트 파일
├── notebooks/               # Jupyter 노트북
├── logs/                   # 로그 파일
├── uv.lock                # 의존성 잠금 파일
└── pyproject.toml         # 프로젝트 설정 파일 
```

## <div align="center">설치 및 설정</div>

### 1. 저장소 복제

```bash
git clone <repository-url>
cd job_scraper
```

### 2. 의존성 설치

```bash
uv sync
```

### 3. 데이터베이스 설정

PostgreSQL 데이터베이스를 생성하고 다음과 같이 설정하세요:

```bash
# 데이터 베이스 생성 및 권한 변경
psql postgres -f grant_permissions.sql
psql -U username -d databasename -f job_scraper_db.sql
```

### 4. 환경 변수 설정

`.env` 파일을 생성하고 데이터베이스 연결 정보를 설정하세요:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=databasename
DB_USER=username
DB_PASSWORD=password
DB_SSL_MODE=prefer
```

## <div align="center">사용법</div>

### 1. 웹 대시보드 실행

```bash
uv run uvicorn job_scraper.web_dashboard.main:app --reload
```

브라우저에서 `http://localhost:8000`에 접속하여 대시보드를 사용할 수 있습니다.

### 2. 커맨드라인 파이프라인 실행

```bash
uv run job_scraper/main_pipeline.py 
```

웹사이트별 설정에 따라 회사별 채용 공고 스크래핑이 시작됩니다.


- `--max-scrolls`: 최대 스크롤 횟수
- `--scroll-delay`: 스크롤 간격 시간 (밀리초)
- `--debug`: 디버그 모드 활성화


## <div align="center">데이터베이스 스키마</div>

### 주요 테이블

- **scraping_batches**: 스크래핑 실행 배치 
- **scraping_tasks**: 각 스테이지 별 작업 
- **companies**: 회사 정보
- **job_posting**: 사이트별 채용 공고
- **job_categories**: 직무 분류
- **locations**: 근무 지역
- **scraped_urls**: 수집한 URL

## <div align="center">모니터링 및 로그</div>

- **구조화된 로그**: 대시보드를 통한 로그 파일 관리
- **실시간 모니터링**: WebSocket을 통한 진행 상황 모니터링
- **성능 메트릭**: 처리 속도, 성공률 등 통계

## <div align="center">테스트 실행</div>

```bash
pytest tests/
```


### 코드 품질관리

프로젝트에 기여하기 전에 코드 품질검사를 실행하세요:

```bash
# 코드 포맷팅
black job_scraper/

# import 정렬
isort job_scraper/

# 코드 품질 검사
flake8 job_scraper/
```


## <div align="center">기여 방법</div>

1. Fork 프로젝트
2. Feature 브랜치 생성 (`git checkout -b feature/기능명`)
3. 변경사항 커밋 (`git commit -am '새 기능 추가'`)
4. 브랜치에 Push (`git push origin feature/기능명`)
5. Pull Request 생성

## <div align="center">라이선스</div>

이 프로젝트는 MIT 라이선스 하에 공개됩니다.
