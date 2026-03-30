"""
기업 유형 분류 Import/Export 서비스.

company_type이 없는 기업을 CSV로 추출하고,
분류된 CSV를 읽어 companies 테이블에 반영하는 로직.
"""

import csv
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import create_development_logger
from app.models.job import Company

logger = create_development_logger(__name__)

VALID_COMPANY_TYPES = {
    "SI",
    "대기업IT",
    "솔루션",
    "IT서비스",
    "웹에이전시",
    "스타트업",
    "미분류",
}

EXPORT_COLUMNS = [
    "company_id",
    "company_name",
    "company_size",
    "is_listed",
    "listing_market",
    "job_count",
]

BATCH_SIZE = 100


def export_companies(
    session: Session,
    output_path: str,
    limit: Optional[int] = None,
    include_all: bool = False,
) -> int:
    """company_type이 없는 기업을 CSV로 추출.

    Args:
        session: DB 세션
        output_path: 출력 CSV 파일 경로
        limit: 최대 추출 건수
        include_all: True면 이미 분류된 기업도 포함

    Returns:
        추출된 행 수
    """
    from sqlalchemy import func
    from app.models.job import JobPosting

    query = (
        session.query(
            Company.company_id,
            Company.company_name,
            Company.company_size,
            Company.is_listed,
            Company.listing_market,
            func.count(JobPosting.id).label("job_count"),
        )
        .outerjoin(JobPosting, Company.company_id == JobPosting.company_id)
        .group_by(Company.company_id)
    )

    if not include_all:
        query = query.filter(Company.company_type.is_(None))

    query = query.order_by(Company.company_id)

    if limit:
        query = query.limit(limit)

    rows = query.all()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "company_id": row.company_id,
                    "company_name": row.company_name or "",
                    "company_size": row.company_size or "",
                    "is_listed": row.is_listed or "",
                    "listing_market": row.listing_market or "",
                    "job_count": row.job_count,
                }
            )

    label = "all" if include_all else "unlabeled"
    logger.info(f"Exported {len(rows)} {label} companies to {output_path}")
    return len(rows)


def import_company_types(
    session: Session,
    csv_path: str,
    dry_run: bool = False,
    skip_existing: bool = False,
) -> dict:
    """CSV를 읽어 companies 테이블의 company_type을 UPDATE.

    CSV 형식: company_id, company_type

    Args:
        session: DB 세션
        csv_path: 입력 CSV 파일 경로
        dry_run: True면 실제 반영 없이 결과만 반환
        skip_existing: True면 이미 값이 있는 기업은 건너뜀

    Returns:
        {"applied": int, "skipped": int, "not_found": int, "invalid_type": int}
    """
    result = {
        "applied": 0,
        "skipped": 0,
        "not_found": 0,
        "invalid_type": 0,
    }

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        if "company_id" not in fieldnames:
            raise ValueError("CSV must contain 'company_id' column")
        if "company_type" not in fieldnames:
            raise ValueError("CSV must contain 'company_type' column")

        batch_count = 0

        for row in reader:
            company_id = row["company_id"].strip()
            if not company_id:
                continue

            company = (
                session.query(Company)
                .filter(Company.company_id == int(company_id))
                .first()
            )

            if not company:
                result["not_found"] += 1
                logger.warning(f"Company not found: {company_id}")
                continue

            company_type = row["company_type"].strip()

            if company_type not in VALID_COMPANY_TYPES:
                result["invalid_type"] += 1
                logger.warning(
                    f"Invalid company_type '{company_type}' "
                    f"for company {company_id} ({company.company_name})"
                )
                continue

            if skip_existing and company.company_type:
                result["skipped"] += 1
                continue

            if not dry_run:
                company.company_type = company_type
                company.source_info = {"claude_code": True}

            result["applied"] += 1
            batch_count += 1

            if not dry_run and batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0

        if not dry_run and batch_count > 0:
            session.commit()

    action = "Dry-run" if dry_run else "Imported"
    logger.info(
        f"{action}: applied={result['applied']}, "
        f"skipped={result['skipped']}, "
        f"not_found={result['not_found']}, "
        f"invalid_type={result['invalid_type']}"
    )
    return result
