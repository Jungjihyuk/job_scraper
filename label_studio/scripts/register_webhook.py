"""
Label Studio webhook 등록.
annotation 생성/수정 이벤트를 backend webhook handler로 전송.

사용법:
    python label_studio/scripts/register_webhook.py
"""

import os
import sys

import requests

from auth import get_auth_headers, LS_URL, PROJECT_ID

BACKEND_URL = os.getenv("BACKEND_WEBHOOK_URL", "http://backend:8000")

headers = get_auth_headers()

# 기존 webhook 확인
existing = requests.get(f"{LS_URL}/api/webhooks", headers=headers)
if existing.status_code == 200:
    for wh in existing.json():
        if "label-studio" in wh.get("url", ""):
            print(f"Webhook already registered: id={wh['id']}, url={wh['url']}")
            sys.exit(0)

# 새 webhook 등록
resp = requests.post(
    f"{LS_URL}/api/webhooks",
    json={
        "project": PROJECT_ID,
        "url": f"{BACKEND_URL}/api/webhooks/label-studio",
        "send_payload": True,
        "send_for_all_actions": False,
        "actions": ["ANNOTATION_CREATED", "ANNOTATION_UPDATED"],
    },
    headers=headers,
)

if resp.status_code == 201:
    wh = resp.json()
    print(f"Webhook registered: id={wh['id']}")
    print(f"  URL: {wh['url']}")
    print(f"  Actions: {wh['actions']}")
else:
    print(f"Failed: {resp.status_code} {resp.text}")
    sys.exit(1)
