# 도메인 라벨링 검수 파이프라인

채용공고의 산업 도메인을 AI(Claude)로 자동 분류하고, Label Studio에서 사람이 검수한 뒤, 검수 결과를 운영 DB에 반영하는 파이프라인.

## 구조

```
label_studio/
  imports/             # Label Studio UI에 import할 CSV 데이터
  exports/             # Label Studio 검수 완료 export
  cli_pipeline/        # CLI 자동 라벨링 파이프라인 작업 디렉토리
  scripts/             # 설정/관리 스크립트
```

## 전체 흐름

```
DB (domain=NULL 공고)
  ↓ import_from_db.py
Label Studio (검수 UI)
  ↓ webhook 또는 export_annotations.py
domain_review_staging (스테이징 테이블)
  ↓ apply_reviewed_domains.py
job_posting.domain (운영 반영)
```

---

## 초기 설정 (최초 1회)

### 1. Label Studio DB 생성

postgres 컨테이너가 이미 실행 중이면 수동으로 DB를 생성해야 합니다.
(최초 `docker compose up`이라면 init 스크립트가 자동 생성합니다.)

```bash
docker exec job_scraper_postgres \
  psql -U jihyeok -d job_scraper_db \
  -c "CREATE DATABASE label_studio_db OWNER jihyeok"
```

### 2. Label Studio 실행

```bash
docker compose up -d postgres label-studio
```

- Label Studio: http://localhost:8080

### 3. Label Studio 계정 생성

브라우저에서 http://localhost:8080 접속 후 회원가입(Sign Up)합니다.

### 4. API Token 발급 -> .env에 등록

1. Label Studio 로그인
2. 우측 상단 프로필 아이콘 -> **Account & Settings**
3. **Access Token** 복사
4. 프로젝트 루트 `.env` 파일에 토큰 입력:

```
LABEL_STUDIO_API_TOKEN=<복사한 토큰>
```

모든 label_studio 스크립트는 `.env`에서 자동으로 환경변수를 읽습니다.

### 5. Webhook 등록

Label Studio에서 검수 완료 시 자동으로 스테이징 테이블에 기록되도록 webhook을 등록합니다.

```bash
uv run label_studio/scripts/register_webhook.py
```

---

## 사용법

### A. 기존 CSV 데이터 import (이미 AI 라벨링 완료된 데이터)

`label_studio/imports/labeling_result_*.csv` 파일이 있는 경우:

```bash
# 1. CSV -> Label Studio import용 JSON 변환
uv run label_studio/scripts/prepare_import_data.py

# 2. 프로젝트 생성 + 데이터 import
uv run label_studio/scripts/setup_project.py
```

### B. DB에서 신규 공고 import (도메인 미분류 데이터)

```bash
uv run label_studio/scripts/import_from_db.py             # 기본 500건
uv run label_studio/scripts/import_from_db.py --limit 200  # 건수 지정
```

### C. Label Studio에서 검수

1. http://localhost:8080 접속
2. 프로젝트 선택
3. 태스크 클릭 -> AI 예측 도메인 확인 -> 올바른 도메인 선택 -> **Submit**

### D. 검수 결과를 운영 DB에 반영

```bash
# 미리보기 (실제 변경 없음)
uv run analysis/scripts/apply_reviewed_domains.py --dry-run

# 실제 반영
uv run analysis/scripts/apply_reviewed_domains.py
```

### E. Webhook 누락 시 수동 동기화

webhook이 실패했거나 데이터가 빠진 경우 Label Studio에서 직접 export합니다.

```bash
uv run label_studio/scripts/export_annotations.py
```

---

## 환경변수

| 변수 | 설명 | 기본값 |
|---|---|---|
| `LABEL_STUDIO_API_TOKEN` | Label Studio API 토큰 | (필수) |
| `LABEL_STUDIO_URL` | Label Studio URL | `http://localhost:8080` |
| `LABEL_STUDIO_PROJECT_ID` | 프로젝트 ID | `1` |

## 도메인 목록 (34개)

IT/소프트웨어, 게임, 건설/부동산, 공공/정책, 광고/마케팅, 교육, 국방/방산, 금융, 농업/식품, 로보틱스, 미디어/엔터테인먼트, 물류/유통, 무역/수출, 바이오/제약, 반도체, 법률, 보안/사이버보안, 블록체인/웹3, 뷰티/화장품, 생활서비스, 스포츠, 식품/외식, 에너지, 여행/관광, 의료/헬스케어, 인사/HR, 자동차/모빌리티, 제조, 커머스, 통신, 패션, 항공/우주, 해양/조선, 미분류
