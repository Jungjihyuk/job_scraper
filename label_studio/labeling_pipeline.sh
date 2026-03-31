#!/bin/bash
# =============================================================================
# labeling_pipeline.sh - Claude Code 기반 자동 라벨링 파이프라인
#
# 사용법:
#   ./label_studio/labeling_pipeline.sh                  # 미라벨링 공고만
#   ./label_studio/labeling_pipeline.sh --all            # 전체 공고 재라벨링
#   ./label_studio/labeling_pipeline.sh --batch-size 20  # 청크 크기 조절
#   ./label_studio/labeling_pipeline.sh --dry-run        # DB 반영 없이 미리보기
# =============================================================================

set -eo pipefail

# ── 설정 ──
BATCH_SIZE=30
DATA_DIR="label_studio/cli_pipeline"
CHUNKS_DIR="$DATA_DIR/chunks"
PROMPT_FILE="$DATA_DIR/LABELING_PROMPT.md"
FINAL_OUTPUT="$DATA_DIR/labeled.csv"
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
            echo "Usage: ./label_studio/labeling_pipeline.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --all            전체 공고 재라벨링 (기존 라벨 포함)"
            echo "  --batch-size N   청크당 행 수 (기본: 30)"
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
echo "=== Step 1: DB에서 공고 추출 ==="
cd backend && uv run app/labeling_cli.py export $EXPORT_FLAG --output "../$DATA_DIR/unlabeled.csv" && cd ..

TOTAL=$(tail -n +2 "$DATA_DIR/unlabeled.csv" | wc -l | tr -d '[:space:]')
echo "총 $TOTAL 건"

if [[ "$TOTAL" -eq 0 ]]; then
    echo "라벨링할 공고가 없습니다."
    exit 0
fi

# =============================================================================
# Step 2: CSV를 청크로 분할
# =============================================================================
echo ""
echo "=== Step 2: ${BATCH_SIZE}건씩 청크 분할 ==="

HEADER=$(head -1 "$DATA_DIR/unlabeled.csv")

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
' "$DATA_DIR/unlabeled.csv"

CHUNK_COUNT=$(ls "$CHUNKS_DIR/"*.csv 2>/dev/null | wc -l | tr -d '[:space:]')
echo "$CHUNK_COUNT 개 청크 생성"

# =============================================================================
# Step 3: 각 청크를 Claude Code로 라벨링
# =============================================================================
echo ""
echo "=== Step 3: Claude Code 라벨링 ==="

# 프롬프트 추출 (``` 마커 사이)
PROMPT=$(sed -n '/^```$/,/^```$/p' "$PROMPT_FILE" | sed '1d;$d')

# labeled.csv 헤더 작성
echo "posting_id,domain_l2,core_technologies" > "$FINAL_OUTPUT"

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
        RESPONSE=$(claude -p "다음 규칙에 따라 CSV 데이터를 라벨링해주세요. 결과는 CSV만 출력하세요. 헤더(posting_id,domain_l2,core_technologies)는 제외하고 데이터 행만 출력하세요. 설명이나 마크다운 코드블록 없이 순수 CSV 행만 출력하세요.

$PROMPT

아래는 라벨링할 CSV 데이터입니다:

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

    # CSV 행 추출 (posting_id가 숫자로 시작하는 행만)
    LABELED_ROWS=$(echo "$RESPONSE" | grep -E '^[0-9]' || true)

    if [[ -n "$LABELED_ROWS" ]]; then
        echo "$LABELED_ROWS" >> "$FINAL_OUTPUT"
        ROW_COUNT=$(echo "$LABELED_ROWS" | wc -l | tr -d '[:space:]')
        TOTAL_LABELED=$((TOTAL_LABELED + ROW_COUNT))
        echo "완료 ($ROW_COUNT건)"
    else
        FAILED=$((FAILED + 1))
        echo "실패 (응답 없음)"
        # 실패한 청크 로그
        echo "$CHUNK" >> "$DATA_DIR/failed_chunks.log"
    fi
done

echo ""
echo "라벨링 결과: ${TOTAL_LABELED}건 성공, ${FAILED}개 청크 실패"

if [[ $TOTAL_LABELED -eq 0 ]]; then
    echo "라벨링된 데이터가 없습니다. 종료합니다."
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

cd backend && uv run app/labeling_cli.py import --input "../$FINAL_OUTPUT" $IMPORT_FLAGS && cd ..

# ── 정리 ──
echo ""
echo "=== 파이프라인 완료 ==="
echo "  추출: $TOTAL 건"
echo "  라벨링: $TOTAL_LABELED 건"
echo "  실패: $FAILED 청크"
echo "  결과 파일: $FINAL_OUTPUT"

if [[ $FAILED -gt 0 ]]; then
    echo "  실패 목록: $DATA_DIR/failed_chunks.log"
    echo ""
    echo "실패한 청크를 재처리하려면:"
    echo "  실패한 청크 파일을 확인 후 개별적으로 Claude에게 라벨링 요청"
fi
