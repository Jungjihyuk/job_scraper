#!/bin/bash
# =============================================================================
# company_type_pipeline.sh - Claude Code 기반 기업 유형 자동 분류 파이프라인
#
# 사용법:
#   ./label_studio/company_type_pipeline.sh                  # 미분류 기업만
#   ./label_studio/company_type_pipeline.sh --all            # 전체 기업 재분류
#   ./label_studio/company_type_pipeline.sh --batch-size 50  # 청크 크기 조절
#   ./label_studio/company_type_pipeline.sh --dry-run        # DB 반영 없이 미리보기
# =============================================================================

set -eo pipefail

# ── 설정 ──
BATCH_SIZE=50
DATA_DIR="label_studio/cli_pipeline"
CHUNKS_DIR="$DATA_DIR/company_chunks"
PROMPT_FILE="$DATA_DIR/COMPANY_TYPE_PROMPT.md"
UNLABELED="$DATA_DIR/companies_unlabeled.csv"
FINAL_OUTPUT="$DATA_DIR/companies_labeled.csv"
MAX_RETRIES=2

# ── 인자 파싱 ──
EXPORT_FLAG=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all) EXPORT_FLAG="--all" ;;
        --batch-size) BATCH_SIZE="$2"; shift ;;
        --dry-run) DRY_RUN=true ;;
        -h|--help)
            echo "Usage: ./label_studio/company_type_pipeline.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --all            전체 기업 재분류 (기존 분류 포함)"
            echo "  --batch-size N   청크당 행 수 (기본: 50)"
            echo "  --dry-run        DB 반영 없이 미리보기"
            echo "  -h, --help       도움말"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# ── 사전 검증 ──
if ! command -v claude &>/dev/null; then
    echo "Error: claude CLI not found. Install Claude Code first."
    exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "Error: $PROMPT_FILE not found."
    exit 1
fi

# ── 초기화 ──
mkdir -p "$CHUNKS_DIR"
rm -f "$CHUNKS_DIR/"*.csv

# =============================================================================
# Step 1: Export
# =============================================================================
echo "=== Step 1: DB에서 기업 추출 ==="
cd backend && uv run app/labeling_cli.py company-export $EXPORT_FLAG --output "../$UNLABELED" && cd ..

TOTAL=$(tail -n +2 "$UNLABELED" | wc -l | tr -d '[:space:]')
echo "총 $TOTAL 건"

if [[ "$TOTAL" -eq 0 ]]; then
    echo "분류할 기업이 없습니다."
    exit 0
fi

# =============================================================================
# Step 2: CSV를 청크로 분할
# =============================================================================
echo ""
echo "=== Step 2: ${BATCH_SIZE}건씩 청크 분할 ==="

HEADER=$(head -1 "$UNLABELED")

awk -v batch="$BATCH_SIZE" -v dir="$CHUNKS_DIR" -v header="$HEADER" '
NR == 1 { next }
{
    chunk = int((NR - 2) / batch)
    file = sprintf("%s/chunk_%03d.csv", dir, chunk)
    if ((NR - 2) % batch == 0) {
        print header > file
    }
    print >> file
}
' "$UNLABELED"

CHUNK_COUNT=$(ls "$CHUNKS_DIR/"*.csv 2>/dev/null | wc -l | tr -d '[:space:]')
echo "$CHUNK_COUNT 개 청크 생성"

# =============================================================================
# Step 3: 각 청크를 Claude Code로 분류
# =============================================================================
echo ""
echo "=== Step 3: Claude Code 기업 유형 분류 ==="

# 프롬프트 추출 (``` 마커 사이)
PROMPT=$(sed -n '/^```$/,/^```$/p' "$PROMPT_FILE" | sed '1d;$d')

# labeled.csv 헤더 작성
echo "company_id,company_type" > "$FINAL_OUTPUT"

COMPLETED=0
FAILED=0
TOTAL_LABELED=0

for CHUNK in "$CHUNKS_DIR"/chunk_*.csv; do
    CHUNK_NAME=$(basename "$CHUNK" .csv)
    CHUNK_ROWS=$(tail -n +2 "$CHUNK" | wc -l | tr -d '[:space:]')
    COMPLETED=$((COMPLETED + 1))

    echo -n "  [$COMPLETED/$CHUNK_COUNT] $CHUNK_NAME ($CHUNK_ROWS건)... "

    # CSV 내용 읽기
    CHUNK_CONTENT=$(cat "$CHUNK")

    # Claude Code 호출 (재시도 포함)
    RESPONSE=""
    for ATTEMPT in $(seq 1 $MAX_RETRIES); do
        RESPONSE=$(claude -p "다음 규칙에 따라 CSV 데이터의 기업 유형을 분류해주세요. 결과는 CSV만 출력하세요. 헤더(company_id,company_type)는 제외하고 데이터 행만 출력하세요. 설명이나 마크다운 코드블록 없이 순수 CSV 행만 출력하세요.

$PROMPT

아래는 분류할 기업 CSV 데이터입니다:

$CHUNK_CONTENT" 2>/dev/null || true)

        # 응답에 숫자로 시작하는 행이 있으면 성공
        if echo "$RESPONSE" | grep -qE '^[0-9]'; then
            break
        fi

        if [[ $ATTEMPT -lt $MAX_RETRIES ]]; then
            echo -n "재시도($((ATTEMPT + 1)))... "
            sleep 2
        fi
    done

    # CSV 행 추출 (company_id가 숫자로 시작하는 행만)
    LABELED_ROWS=$(echo "$RESPONSE" | grep -E '^[0-9]' || true)

    if [[ -n "$LABELED_ROWS" ]]; then
        echo "$LABELED_ROWS" >> "$FINAL_OUTPUT"
        ROW_COUNT=$(echo "$LABELED_ROWS" | wc -l | tr -d '[:space:]')
        TOTAL_LABELED=$((TOTAL_LABELED + ROW_COUNT))
        echo "완료 ($ROW_COUNT건)"
    else
        FAILED=$((FAILED + 1))
        echo "실패 (응답 없음)"
        echo "$CHUNK" >> "$DATA_DIR/company_failed_chunks.log"
    fi
done

echo ""
echo "분류 결과: ${TOTAL_LABELED}건 성공, ${FAILED}개 청크 실패"

if [[ $TOTAL_LABELED -eq 0 ]]; then
    echo "분류된 데이터가 없습니다. 종료합니다."
    exit 1
fi

# =============================================================================
# Step 4: DB 반영
# =============================================================================
echo ""
echo "=== Step 4: DB 반영 ==="

IMPORT_FLAGS=""
if $DRY_RUN; then
    IMPORT_FLAGS="--dry-run"
fi

cd backend && uv run app/labeling_cli.py company-import --input "../$FINAL_OUTPUT" $IMPORT_FLAGS && cd ..

# ── 정리 ──
echo ""
echo "=== 파이프라인 완료 ==="
echo "  추출: $TOTAL 건"
echo "  분류: $TOTAL_LABELED 건"
echo "  실패: $FAILED 청크"
echo "  결과 파일: $FINAL_OUTPUT"

if [[ $FAILED -gt 0 ]]; then
    echo "  실패 목록: $DATA_DIR/company_failed_chunks.log"
fi
