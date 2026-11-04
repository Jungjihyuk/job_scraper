"""
staging → production UPSERT: 검수 완료된 도메인 데이터를 job_posting 테이블에 반영.

사용법:
    cd backend && uv run python ../analysis/scripts/apply_reviewed_domains.py
    cd backend && uv run python ../analysis/scripts/apply_reviewed_domains.py --dry-run
    cd backend && uv run python ../analysis/scripts/apply_reviewed_domains.py --batch-size 500
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import db_manager, init_database
from app.core.logging import create_development_logger
from app.services.labeling import DOMAIN_L2_TO_L1, LEGACY_L2_TO_STANDARD_L2
from sqlalchemy import text

logger = create_development_logger(__name__)


def apply_reviewed_domains(batch_size: int = 100, dry_run: bool = False):
    """
    domain_review_staging에서 status='pending'인 행을 읽어
    job_posting.domain_l2/domain_l1을 UPDATE한다.
    reviewed_domain은 L2 값이며, L1은 DOMAIN_L2_TO_L1로 역산한다.
    """
    if not init_database():
        logger.error("Failed to initialize database")
        return False

    try:
        with db_manager.get_session() as session:
            # pending 레코드 조회
            rows = session.execute(
                text("""
                    SELECT id, posting_id, reviewed_domain
                    FROM domain_review_staging
                    WHERE status = 'pending'
                    ORDER BY reviewed_at
                    LIMIT :limit
                """),
                {"limit": batch_size},
            ).fetchall()

            if not rows:
                print("No pending records to apply")
                return True

            print(f"Found {len(rows)} pending records")

            applied = 0
            skipped = 0

            for row in rows:
                staging_id, posting_id, reviewed_domain = row
                domain_l2 = LEGACY_L2_TO_STANDARD_L2.get(
                    reviewed_domain, reviewed_domain
                )

                # job_posting에서 해당 posting_id 존재 확인
                exists = session.execute(
                    text(
                        "SELECT 1 FROM job_posting WHERE posting_id = :pid"
                    ),
                    {"pid": posting_id},
                ).fetchone()

                if not exists or domain_l2 not in DOMAIN_L2_TO_L1:
                    reason = (
                        "not found"
                        if not exists
                        else f"invalid domain L2 '{reviewed_domain}'"
                    )
                    logger.warning(f"posting_id {posting_id} {reason}, marking rejected")
                    if not dry_run:
                        session.execute(
                            text("""
                                UPDATE domain_review_staging
                                SET status = 'rejected', applied_at = :now
                                WHERE id = :id
                            """),
                            {"id": staging_id, "now": datetime.utcnow()},
                        )
                    skipped += 1
                    continue

                domain_l1 = DOMAIN_L2_TO_L1[domain_l2]

                if dry_run:
                    print(f"  [DRY RUN] {posting_id}: -> {domain_l1} › {domain_l2}")
                else:
                    # Production 테이블 UPDATE
                    session.execute(
                        text("""
                            UPDATE job_posting
                            SET domain_l2 = :domain_l2, domain_l1 = :domain_l1
                            WHERE posting_id = :pid
                        """),
                        {
                            "domain_l2": domain_l2,
                            "domain_l1": domain_l1,
                            "pid": posting_id,
                        },
                    )
                    # Staging status 업데이트
                    session.execute(
                        text("""
                            UPDATE domain_review_staging
                            SET status = 'applied', applied_at = :now
                            WHERE id = :id
                        """),
                        {"id": staging_id, "now": datetime.utcnow()},
                    )

                applied += 1

            print(f"\nResults: applied={applied}, skipped={skipped}")
            if dry_run:
                print("(dry-run mode: no changes committed)")

            return True

    except Exception as e:
        logger.error(f"Apply failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="검수 완료 도메인을 운영 DB에 반영"
    )
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기만")
    parser.add_argument("--batch-size", type=int, default=100, help="한 번에 처리할 건수")
    args = parser.parse_args()

    success = apply_reviewed_domains(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    sys.exit(0 if success else 1)
