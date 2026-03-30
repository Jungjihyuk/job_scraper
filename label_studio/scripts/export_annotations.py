"""
Label Studio에서 annotation을 export하여 staging 테이블에 적재.
도메인 + 기술스택 결과를 모두 처리.

사용법:
    python label_studio/scripts/export_annotations.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests
from sqlalchemy import text

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from auth import get_auth_headers, LS_URL, PROJECT_ID
from backend.core.database import db_manager, init_database
from backend.core.logging import create_development_logger

logger = create_development_logger(__name__)


def export_and_stage():
    headers = get_auth_headers()

    resp = requests.get(
        f"{LS_URL}/api/projects/{PROJECT_ID}/export?exportType=JSON",
        headers=headers,
    )
    if resp.status_code != 200:
        print(f"Export failed: {resp.status_code} {resp.text[:200]}")
        return

    tasks = resp.json()
    print(f"Exported {len(tasks)} tasks from Label Studio")

    if not init_database():
        logger.error("Failed to initialize database")
        return

    domain_count = 0
    tech_count = 0
    skipped_count = 0

    with db_manager.get_session() as session:
        for task in tasks:
            annotations = task.get("annotations", [])
            if not annotations:
                skipped_count += 1
                continue

            # 가장 최근 annotation 사용
            annotation = sorted(
                annotations,
                key=lambda a: a.get("updated_at", ""),
                reverse=True,
            )[0]

            posting_id = task["data"].get("posting_id")
            annotation_id = annotation["id"]

            # result에서 domain, core_technologies, custom 입력, note 추출
            domain = None
            custom_domain = None
            core_technologies = []
            custom_techs = []
            note = None
            for item in annotation.get("result", []):
                if item.get("from_name") == "domain":
                    choices = item.get("value", {}).get("choices", [])
                    if choices:
                        domain = choices[0]
                elif item.get("from_name") == "custom_domain":
                    texts = item.get("value", {}).get("text", [])
                    if texts and texts[0].strip():
                        custom_domain = texts[0].strip()
                elif item.get("from_name") == "core_technologies":
                    # Taxonomy: [[category, tech], [category, tech], ...]
                    taxonomy = item.get("value", {}).get("taxonomy", [])
                    for path in taxonomy:
                        if len(path) >= 2:
                            core_technologies.append(path[-1])  # leaf = 기술명
                        elif len(path) == 1:
                            core_technologies.append(path[0])
                elif item.get("from_name") == "custom_techs":
                    texts = item.get("value", {}).get("text", [])
                    if texts and texts[0].strip():
                        # 콤마 구분 파싱
                        custom_techs = [t.strip() for t in texts[0].split(",") if t.strip()]
                elif item.get("from_name") == "review_note":
                    texts = item.get("value", {}).get("text", [])
                    if texts:
                        note = texts[0]

            # custom_domain이 있으면 도메인 대체
            if custom_domain:
                domain = custom_domain

            # custom_techs를 core_technologies에 병합
            if custom_techs:
                existing = set(core_technologies)
                for t in custom_techs:
                    if t not in existing:
                        core_technologies.append(t)

            if not posting_id:
                skipped_count += 1
                continue

            ai_domain = task["data"].get("ai_domain")
            ai_techs_str = task["data"].get("ai_techs", "")

            # 도메인 staging UPSERT
            if domain:
                session.execute(
                    text("""
                        INSERT INTO domain_review_staging
                            (posting_id, reviewed_domain, ai_predicted_domain,
                             reviewer_note, annotation_id, reviewed_at, status)
                        VALUES
                            (:posting_id, :domain, :ai_domain,
                             :note, :annotation_id, :reviewed_at, 'pending')
                        ON CONFLICT (posting_id, annotation_id) DO UPDATE SET
                            reviewed_domain = EXCLUDED.reviewed_domain,
                            reviewer_note = EXCLUDED.reviewer_note,
                            reviewed_at = EXCLUDED.reviewed_at,
                            status = CASE
                                WHEN domain_review_staging.status = 'applied'
                                THEN 'applied'
                                ELSE 'pending'
                            END
                    """),
                    {
                        "posting_id": str(posting_id),
                        "domain": domain,
                        "ai_domain": ai_domain,
                        "note": note,
                        "annotation_id": annotation_id,
                        "reviewed_at": datetime.utcnow(),
                    },
                )
                domain_count += 1

            # 기술스택 staging UPSERT
            if core_technologies:
                ai_techs_list = [
                    t.strip()
                    for t in ai_techs_str.split(",")
                    if t.strip() and t.strip() != "추출된 기술 없음"
                ]

                session.execute(
                    text("""
                        INSERT INTO core_tech_review_staging
                            (posting_id, reviewed_technologies, ai_predicted_technologies,
                             reviewer_note, annotation_id, reviewed_at, status)
                        VALUES
                            (:posting_id, :reviewed_techs, :ai_techs,
                             :note, :annotation_id, :reviewed_at, 'pending')
                        ON CONFLICT (posting_id, annotation_id) DO UPDATE SET
                            reviewed_technologies = EXCLUDED.reviewed_technologies,
                            reviewer_note = EXCLUDED.reviewer_note,
                            reviewed_at = EXCLUDED.reviewed_at,
                            status = CASE
                                WHEN core_tech_review_staging.status = 'applied'
                                THEN 'applied'
                                ELSE 'pending'
                            END
                    """),
                    {
                        "posting_id": str(posting_id),
                        "reviewed_techs": json.dumps(core_technologies, ensure_ascii=False),
                        "ai_techs": json.dumps(ai_techs_list, ensure_ascii=False),
                        "note": note,
                        "annotation_id": annotation_id,
                        "reviewed_at": datetime.utcnow(),
                    },
                )
                tech_count += 1

    print(f"\nResults:")
    print(f"  Domain staged: {domain_count}")
    print(f"  Core tech staged: {tech_count}")
    print(f"  Skipped (no annotation): {skipped_count}")


if __name__ == "__main__":
    export_and_stage()
