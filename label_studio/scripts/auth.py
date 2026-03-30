"""
Label Studio JWT 인증 헬퍼.
.env의 refresh token으로 access token을 자동 발급받아 API 헤더를 반환.
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

LS_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LS_REFRESH_TOKEN = os.getenv("LABEL_STUDIO_API_TOKEN")
PROJECT_ID = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "1"))


def get_auth_headers() -> dict:
    """refresh token으로 access token을 발급받아 Bearer 헤더 반환."""
    if not LS_REFRESH_TOKEN:
        print("Error: LABEL_STUDIO_API_TOKEN이 설정되지 않았습니다.")
        print("  .env 파일에 LABEL_STUDIO_API_TOKEN=<token> 을 추가하세요.")
        sys.exit(1)

    resp = requests.post(
        f"{LS_URL}/api/token/refresh",
        json={"refresh": LS_REFRESH_TOKEN},
        timeout=10,
    )

    if resp.status_code != 200:
        print(f"Error: access token 발급 실패 ({resp.status_code})")
        print(f"  {resp.text[:200]}")
        print("  Label Studio UI에서 Access Token을 다시 복사하여 .env에 등록하세요.")
        sys.exit(1)

    access_token = resp.json()["access"]
    return {"Authorization": f"Bearer {access_token}"}
