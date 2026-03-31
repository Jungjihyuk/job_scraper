FROM ghcr.io/astral-sh/uv:python3.10-bookworm

WORKDIR /app

# 의존성 파일만 먼저 복사 (캐시 레이어 활용)
COPY backend/pyproject.toml backend/uv.lock ./

# Python 패키지 설치 + Playwright 브라우저 설치 (빌드 시 1회만)
RUN uv sync && uv run playwright install --with-deps chromium
