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

### 스크래핑 파이프라인

1. **URL Collector** — 구인구직 사이트 채용 공고 URL 수집
2. **URL Validator** — 수집된 URL 유효성 검증
3. **Content Scraper** — 사이트별 콘텐츠 추출 (Playwright)
4. **Normalizer** — 도메인·핵심 기술·경력 데이터 정규화
5. **Database Saver** — 정제된 데이터를 DB에 저장

### 웹 대시보드

- WebSocket 기반 실시간 스크래핑 모니터링
- 도메인·기술별 통계 차트 및 필터
- 기업 유형별 통계 및 필터
- RESTful API를 통한 데이터 접근

### 데이터 라벨링

- Label Studio 기반 도메인/기술스택 검수 파이프라인
- Claude Code CLI 기반 자동 라벨링 (`labeling_pipeline.sh`, `company_type_pipeline.sh`)
- AI 자동 예측 + 사람 검수 워크플로우

### Taxonomy 관리

- YAML 기반 분류 체계 관리 (도메인 / 핵심 기술 / 기업 유형 / 직무 특성)
- 버전 관리 및 변경 이력 추적 (`CHANGELOG.md`)
- Taxonomy 변경 시 기존 데이터 자동 재라벨링 파이프라인

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | Python 3.10+, FastAPI, SQLAlchemy 2.0+, PostgreSQL |
| 프론트엔드 | React, TypeScript, Vite (FSD 아키텍처) |
| 스크래핑 | Playwright, BeautifulSoup4, httpx |
| 분석/라벨링 | Label Studio, Jupyter, pandas |
| DB 마이그레이션 | Alembic |
| 인프라 | Docker Compose, uv, pnpm |

## 프로젝트 구조

```
job_scraper/
├── backend/                 # 백엔드 프로젝트 루트 (pyproject.toml, alembic.ini)
│   └── app/                 #   FastAPI 서버 + 스크래핑 파이프라인
│       ├── alembic/         #     DB 마이그레이션 (env.py, versions/)
│       ├── api/routes/      #     API 엔드포인트
│       ├── core/            #     설정, DB, 로깅
│       ├── models/          #     SQLAlchemy ORM
│       ├── pipeline/        #     파이프라인 (stages, scrapers, normalizers)
│       │   └── diagnostics/ #     스크래퍼 진단 도구
│       ├── schemas/         #     Pydantic 스키마
│       ├── services/        #     비즈니스 로직 (라벨링, taxonomy, 재라벨링)
│       ├── utils/           #     유틸리티
│       ├── cli.py           #     CLI 스크래핑 파이프라인 실행
│       └── labeling_cli.py  #     CLI 라벨링 파이프라인 실행
├── frontend/                # React 프론트엔드 (FSD)
├── label_studio/            # Label Studio 연동 + Taxonomy
│   ├── cli_pipeline/        #   Claude Code 기반 자동 라벨링
│   ├── datasets/            #   라벨링 입력 CSV
│   ├── exports/             #   검수 완료 export
│   ├── scripts/             #   import/export/설정 스크립트
│   └── taxonomy/            #   분류 체계 YAML (도메인/기술/기업유형/직무특성)
├── analysis/                # 데이터 분석 (Jupyter, 별도 pyproject.toml)
│   ├── notebooks/           #   분석 노트북
│   ├── scripts/             #   데이터 처리 스크립트
│   └── outputs/             #   분석 결과 CSV
├── docs/                    # 프로젝트 문서
├── tests/                   # 테스트
└── docker-compose.yml
```

## 설치 및 실행

### 1. 의존성 설치

```bash
git clone <repository-url>
cd job_scraper/backend
uv sync
```

### 2. 환경 변수 설정

```env
# .env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=job_scraper_db
DB_USER=username
DB_PASSWORD=password
```

### 3. Docker 서비스 실행

```bash
docker compose up -d
```

PostgreSQL(`:5433`), Label Studio(`:8080`) 서비스가 시작됩니다.

### 4. DB 마이그레이션 적용

```bash
cd backend && uv run alembic upgrade head
```

### 5. 사용

```bash
# 웹 대시보드
cd backend && uv run uvicorn app.main:app --reload    # http://localhost:8000

# CLI 스크래핑
cd backend && uv run app/cli.py
cd backend && uv run app/cli.py --max-scrolls 5 --debug

# 프론트엔드 개발 서버
cd frontend/apps/web && pnpm dev                      # http://localhost:5173
```

## CLI 라벨링 파이프라인

```bash
# 도메인/기술 라벨링
cd backend && uv run app/labeling_cli.py export -o ../label_studio/cli_pipeline/unlabeled.csv
cd backend && uv run app/labeling_cli.py import -i ../label_studio/cli_pipeline/labeled.csv

# 기업 유형 분류
cd backend && uv run app/labeling_cli.py company-export -o ../label_studio/cli_pipeline/companies_unlabeled.csv
cd backend && uv run app/labeling_cli.py company-import -i ../label_studio/cli_pipeline/companies_labeled.csv

# Taxonomy 기반 재라벨링 (분류 기준 변경 시)
cd backend && uv run app/labeling_cli.py relabel --dry-run          # 영향 범위 확인
cd backend && uv run app/labeling_cli.py relabel                    # 전체 재라벨링
cd backend && uv run app/labeling_cli.py relabel --target domain    # 도메인만
cd backend && uv run app/labeling_cli.py relabel --target technology --limit 500

# Shell 기반 자동 라벨링 (Claude Code CLI 활용)
./label_studio/labeling_pipeline.sh --dry-run
./label_studio/company_type_pipeline.sh --batch-size 50
```

## DB 마이그레이션 (Alembic)

Alembic 설정 파일은 `backend/alembic.ini`, 마이그레이션 스크립트는 `backend/app/alembic/` 에 위치합니다.

```bash
# 현재 마이그레이션 상태 확인
cd backend && uv run alembic current

# 최신 버전으로 마이그레이션 적용
cd backend && uv run alembic upgrade head

# 한 단계 롤백
cd backend && uv run alembic downgrade -1

# 마이그레이션 이력 확인
cd backend && uv run alembic history

# ORM 모델 변경 후 자동 마이그레이션 생성
cd backend && uv run alembic revision --autogenerate -m "description"
```

### 마이그레이션 파일 구조

```
backend/app/alembic/
├── env.py                  # Alembic 환경 설정 (.env에서 DB URL 로드)
├── script.py.mako          # 마이그레이션 파일 템플릿
└── versions/
    ├── 0001_baseline_existing_schema.py
    ├── 0002_add_company_classification_columns.py
    ├── 0003_add_taxonomy_version_columns.py
    ├── 927955153611_add_specialty_l1_specialty_l2_.py
    └── 5426883d0c04_add_region_column_to_locations.py
```

### 마이그레이션 작성 규칙

- 파일명: `NNNN_설명.py` (순번 기반)
- `revision` / `down_revision` 으로 체인 연결
- `upgrade()` / `downgrade()` 양방향 작성 필수
- ORM 모델(`backend/app/models/`)을 먼저 수정한 뒤 `--autogenerate`로 생성하거나, 수동으로 작성

## 데이터베이스 스키마

| 테이블 | 설명 |
|--------|------|
| `job_posting` | 채용 공고 (도메인, 핵심 기술, specialty_l1/l2, taxonomy 버전 포함) |
| `companies` | 회사 정보 (유형 분류, Blind 평점) |
| `experience_categories` | 경력 정규화 매핑 |
| `scraping_batches` | 스크래핑 실행 배치 |
| `scraping_tasks` | 스테이지별 작업 |
| `job_categories` | 직무 분류 |
| `locations` | 근무 지역 (region 시/도 단위 포함) |
| `scraped_urls` | 수집된 URL |
| `domain_review_staging` | 도메인 라벨링 검수 데이터 |
| `core_tech_review_staging` | 기술 라벨링 검수 데이터 |

## 문서

자세한 설계 문서는 `docs/` 폴더를 참고하세요.

## 라이선스

MIT License
