"""
DB에서 domain_l2가 NULL인 채용공고를 Label Studio에 자동 import.
새로운 공고가 수집될 때마다 실행하여 라벨링 대상을 추가.
포지션 상세, 주요 업무, 자격요건, 우대사항을 모두 포함.

사용법:
    cd backend && uv run ../label_studio/scripts/import_from_db.py
    cd backend && uv run ../label_studio/scripts/import_from_db.py --limit 200
"""

import argparse
import html
import json
import sys
from pathlib import Path

import requests
from sqlalchemy import text

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from auth import get_auth_headers, LS_URL, PROJECT_ID
from app.core.database import db_manager, init_database
from app.core.logging import create_development_logger

logger = create_development_logger(__name__)


def _format_html(text: str) -> str:
    """• 또는 · 기준 줄바꿈 HTML 변환."""
    if not text:
        return "<em>내용 없음</em>"
    text = html.escape(text)
    parts = text.split("•")
    if len(parts) > 1:
        text = parts[0] + "".join(f"<br>• {p.strip()}" for p in parts[1:])
    parts = text.split("·")
    if len(parts) > 1:
        text = parts[0] + "".join(f"<br>· {p.strip()}" for p in parts[1:])
    return text


# 이미 import한 posting_id 추적 파일
IMPORTED_IDS_FILE = Path(__file__).parent / ".imported_posting_ids.json"


def load_imported_ids() -> set:
    if IMPORTED_IDS_FILE.exists():
        with open(IMPORTED_IDS_FILE) as f:
            return set(json.load(f))
    return set()


def save_imported_ids(ids: set):
    with open(IMPORTED_IDS_FILE, "w") as f:
        json.dump(sorted(ids), f)


def fetch_unlabeled_postings(limit: int = 500) -> list[dict]:
    """domain_l2가 NULL인 채용공고를 DB에서 조회 (상세 컬럼 포함)"""
    if not init_database():
        return []

    with db_manager.get_session() as session:
        rows = session.execute(
            text("""
                SELECT posting_id, position,
                       LEFT(position_detail, 2000) as position_detail,
                       LEFT(main_tasks, 2000) as main_tasks,
                       LEFT(requirements, 2000) as requirements,
                       LEFT(preferred, 2000) as preferred,
                       core_technologies
                FROM job_posting
                WHERE domain_l2 IS NULL
                ORDER BY posted_date DESC NULLS LAST
                LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()

        return [
            {
                "posting_id": str(row[0]),
                "position": row[1] or "",
                "position_detail": row[2] or "",
                "main_tasks": row[3] or "",
                "requirements": row[4] or "",
                "preferred": row[5] or "",
                "core_technologies": row[6] or [],
            }
            for row in rows
        ]


def import_to_label_studio(postings: list[dict], imported_ids: set) -> int:
    """Label Studio REST API로 import (중복 제외)"""
    headers = get_auth_headers()

    # 이미 import된 것 제외
    new_postings = [p for p in postings if p["posting_id"] not in imported_ids]
    if not new_postings:
        print("No new postings to import (all already imported)")
        return 0

    tasks = [
        {
            "data": {
                "posting_id": p["posting_id"],
                "position": p["position"],
                "position_detail": _format_html(p["position_detail"]),
                "main_tasks": _format_html(p["main_tasks"]),
                "requirements": _format_html(p["requirements"]),
                "preferred": _format_html(p["preferred"]),
                "ai_domain": "미분류",
                "ai_techs": ", ".join(p["core_technologies"]) or "추출된 기술 없음",
            }
        }
        for p in new_postings
    ]

    BATCH_SIZE = 100
    total_imported = 0

    for i in range(0, len(tasks), BATCH_SIZE):
        batch = tasks[i : i + BATCH_SIZE]
        resp = requests.post(
            f"{LS_URL}/api/projects/{PROJECT_ID}/import",
            json=batch,
            headers=headers,
        )
        if resp.status_code == 201:
            count = resp.json().get("task_count", len(batch))
            total_imported += count
        else:
            logger.error(f"Import error at batch {i}: {resp.status_code}")

    # import된 ID 기록
    for p in new_postings[:total_imported]:
        imported_ids.add(p["posting_id"])

    return total_imported


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DB -> Label Studio import")
    parser.add_argument("--limit", type=int, default=500, help="최대 import 건수")
    args = parser.parse_args()

    imported_ids = load_imported_ids()
    postings = fetch_unlabeled_postings(limit=args.limit)

    if not postings:
        print("No unlabeled postings found in DB")
        sys.exit(0)

    print(f"Found {len(postings)} unlabeled postings in DB")
    count = import_to_label_studio(postings, imported_ids)
    save_imported_ids(imported_ids)
    print(f"Imported {count} new tasks to Label Studio")
