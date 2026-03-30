# Job Scraper

채용 트렌드 분석과 맞춤형 채용공고 추천을 위한 데이터 수집·분석 시스템

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)

## 프로젝트 개요

다양한 채용 사이트에서 공고를 수집하고, **도메인·핵심 기술 태깅**과 **데이터 라벨링**을 통해 정제된 데이터를 기반으로 구직 결정을 돕습니다.


## 주요 기능

### 파이프라인

1. **URL Collector** — 구인구직 사이트 채용 공고 URL 수집
2. **URL Validator** — 수집된 URL 유효성 검증
3. **Content Scraper** — 사이트별 콘텐츠 추출 (Playwright)
4. **Normalizer** — 도메인·핵심 기술·경력 데이터 정규화
5. **Database Saver** — 정제된 데이터를 DB에 저장

### 웹 대시보드

- WebSocket 기반 실시간 스크래핑 모니터링
- 도메인·기술별 통계 차트 및 필터
- RESTful API를 통한 데이터 접근

### 데이터 라벨링

- Label Studio 기반 도메인/기술스택 검수 파이프라인
- AI 자동 예측 + 사람 검수 워크플로우

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | Python 3.10+, FastAPI, SQLAlchemy 2.0+, PostgreSQL |
| 프론트엔드 | React, TypeScript, Vite (FSD 아키텍처) |
| 스크래핑 | Playwright, BeautifulSoup4, httpx |
| 분석/라벨링 | Label Studio, Jupyter, pandas |
| 인프라 | Docker Compose, uv, pnpm |

## 프로젝트 구조

```
job_scraper/
├── backend/                 # FastAPI 서버 + 스크래핑 파이프라인
│   ├── api/routes/          #   API 엔드포인트
│   ├── core/                #   설정, DB, 로깅
│   ├── models/              #   SQLAlchemy ORM
│   ├── pipeline/            #   파이프라인 (stages, scrapers, normalizers)
│   │   └── diagnostics/     #   스크래퍼 진단 도구
│   ├── schemas/             #   Pydantic 스키마
│   ├── utils/               #   유틸리티
│   └── cli.py               #   CLI 파이프라인 실행
├── frontend/                # React 프론트엔드 (FSD)
├── label_studio/            # Label Studio 연동
│   ├── datasets/            #   라벨링 입력 CSV
│   ├── exports/             #   검수 완료 export
│   └── scripts/             #   import/export/설정 스크립트
├── analysis/                # 데이터 분석 (Jupyter, 별도 pyproject.toml)
│   ├── notebooks/           #   분석 노트북
│   ├── scripts/             #   데이터 처리 스크립트
│   └── outputs/             #   분석 결과 CSV
├── docs/                    # 프로젝트 문서
├── tests/                   # 테스트
├── docker-compose.yml
└── pyproject.toml
```

## 설치 및 실행

### 1. 의존성 설치

```bash
git clone <repository-url>
cd job_scraper
uv sync
```

### 2. 환경 변수 설정

```env
# .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=job_scraper_db
DB_USER=username
DB_PASSWORD=password
```

### 3. Docker 서비스 실행

```bash
docker compose up -d
```

PostgreSQL, Label Studio(`:8080`) 서비스가 시작됩니다.

### 4. 사용

```bash
# 웹 대시보드
uv run uvicorn backend.main:app --reload    # http://localhost:8000

# CLI 스크래핑
uv run backend/cli.py
uv run backend/cli.py --max-scrolls 5 --debug

# 프론트엔드 개발 서버
cd frontend/apps/web && pnpm dev            # http://localhost:5173
```

## 데이터베이스 스키마

| 테이블 | 설명 |
|--------|------|
| `job_posting` | 채용 공고 (도메인, 핵심 기술 포함) |
| `companies` | 회사 정보 |
| `scraping_batches` | 스크래핑 실행 배치 |
| `scraping_tasks` | 스테이지별 작업 |
| `job_categories` | 직무 분류 |
| `locations` | 근무 지역 |
| `scraped_urls` | 수집된 URL |
| `domain_review_staging` | 도메인 라벨링 검수 데이터 |

## 문서

자세한 설계 문서는 `docs/` 폴더를 참고하세요.

## 라이선스

MIT License
