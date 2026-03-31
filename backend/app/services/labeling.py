"""
CSV 기반 라벨 Import/Export 서비스.

스크래핑 후 domain/core_technologies가 누락된 공고를 CSV로 추출하고,
라벨링된 CSV를 읽어 DB에 반영하는 핵심 로직.
"""

import csv
import json
from pathlib import Path
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.logging import create_development_logger
from app.models.job import JobPosting

logger = create_development_logger(__name__)

EXPORT_COLUMNS = [
    "posting_id",
    "position",
    "position_detail",
    "main_tasks",
    "requirements",
    "preferred",
    "domain_l2",
    "core_technologies",
]

BATCH_SIZE = 100

# L2 → L1 매핑 (DB에는 L2만 저장, L1은 코드에서 역산)
DOMAIN_L2_TO_L1 = {
    # IT
    "AI/딥테크": "IT",
    "SaaS/B2B": "IT",
    "보안": "IT",
    "소셜/커뮤니티": "IT",
    # 금융
    "핀테크": "금융",
    "전통금융": "금융",
    "블록체인": "금융",
    # 제조/하드웨어
    "반도체": "제조/하드웨어",
    "자동차/모빌리티": "제조/하드웨어",
    "로보틱스": "제조/하드웨어",
    "에너지": "제조/하드웨어",
    "항공/우주": "제조/하드웨어",
    "해양/조선": "제조/하드웨어",
    "일반제조": "제조/하드웨어",
    # 바이오/의료
    "바이오/제약": "바이오/의료",
    "디지털헬스": "바이오/의료",
    "의료기기": "바이오/의료",
    # 유통/소비재
    "커머스": "유통/소비재",
    "물류/유통": "유통/소비재",
    "식품/외식": "유통/소비재",
    "패션": "유통/소비재",
    "뷰티/화장품": "유통/소비재",
    "농업": "유통/소비재",
    # 생활/전문서비스
    "교육": "생활/전문서비스",
    "생활서비스": "생활/전문서비스",
    "여행/관광": "생활/전문서비스",
    "부동산/건설": "생활/전문서비스",
    "인사/HR": "생활/전문서비스",
    "법률": "생활/전문서비스",
    "광고/마케팅": "생활/전문서비스",
    "스포츠": "생활/전문서비스",
    # 미디어/콘텐츠
    "미디어/엔터테인먼트": "미디어/콘텐츠",
    # 게임
    "게임": "게임",
    # 공공/국방
    "공공/정책": "공공/국방",
    "국방/방산": "공공/국방",
    # 통신
    "통신": "통신",
    # 미분류
    "미분류": "미분류",
}

# L1 → L2 목록 (통계/검증용)
DOMAIN_L1_TO_L2S = {}
for l2, l1 in DOMAIN_L2_TO_L1.items():
    DOMAIN_L1_TO_L2S.setdefault(l1, []).append(l2)


def get_domain_l1(domain_l2: str) -> str:
    """L2 도메인에서 L1을 역산."""
    return DOMAIN_L2_TO_L1.get(domain_l2, "미분류")


def export_postings(
    session: Session,
    output_path: str,
    field: Optional[str] = None,
    limit: Optional[int] = None,
    include_all: bool = False,
) -> int:
    """공고를 CSV로 추출.

    Args:
        session: DB 세션
        output_path: 출력 CSV 파일 경로
        field: 필터 대상 ('domain', 'technology', None=둘 다)
        limit: 최대 추출 건수
        include_all: True면 이미 라벨링된 것도 포함

    Returns:
        추출된 행 수
    """
    query = session.query(JobPosting)

    if not include_all:
        if field == "domain":
            query = query.filter(JobPosting.domain_l2.is_(None))
        elif field == "technology":
            query = query.filter(JobPosting.core_technologies.is_(None))
        else:
            query = query.filter(
                or_(
                    JobPosting.domain_l2.is_(None),
                    JobPosting.core_technologies.is_(None),
                )
            )

    query = query.order_by(JobPosting.id)

    if limit:
        query = query.limit(limit)

    rows = query.all()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()

        for row in rows:
            core_tech = row.core_technologies
            if core_tech is not None:
                core_tech = json.dumps(core_tech, ensure_ascii=False)

            writer.writerow(
                {
                    "posting_id": row.posting_id,
                    "position": row.position or "",
                    "position_detail": row.position_detail or "",
                    "main_tasks": row.main_tasks or "",
                    "requirements": row.requirements or "",
                    "preferred": row.preferred or "",
                    "domain_l2": row.domain_l2 or "",
                    "core_technologies": core_tech or "",
                }
            )

    label = "all" if include_all else "unlabeled"
    logger.info(f"Exported {len(rows)} {label} postings to {output_path}")
    return len(rows)


def import_labeled(
    session: Session,
    csv_path: str,
    dry_run: bool = False,
    skip_existing: bool = False,
) -> dict:
    """CSV를 읽어 job_posting 테이블에 직접 UPDATE.

    CSV는 두 가지 형식을 지원:
    - L1/L2 형식: posting_id, domain_l1, domain_l2, core_technologies
    - flat 형식: posting_id, domain, core_technologies (하위 호환)

    DB에는 domain_l2 값을 domain 컬럼에 저장. L1은 코드에서 매핑.

    Args:
        session: DB 세션
        csv_path: 입력 CSV 파일 경로
        dry_run: True면 실제 반영 없이 결과만 반환
        skip_existing: True면 이미 값이 있는 필드는 건너뜀

    Returns:
        {"applied": int, "skipped": int, "not_found": int, "invalid_domain": int}
    """
    result = {"applied": 0, "skipped": 0, "not_found": 0, "invalid_domain": 0}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # L1/L2 형식 감지
        has_domain_l2 = "domain_l2" in fieldnames
        has_domain = "domain" in fieldnames
        has_tech = "core_technologies" in fieldnames

        if not has_domain_l2 and not has_domain and not has_tech:
            raise ValueError(
                "CSV must contain at least 'domain_l2' (or 'domain') "
                "or 'core_technologies' column"
            )

        if "posting_id" not in fieldnames:
            raise ValueError("CSV must contain 'posting_id' column")

        batch_count = 0

        for row in reader:
            posting_id = row["posting_id"].strip()
            if not posting_id:
                continue

            posting = (
                session.query(JobPosting)
                .filter(JobPosting.posting_id == posting_id)
                .first()
            )

            if not posting:
                result["not_found"] += 1
                logger.warning(f"Posting not found: {posting_id}")
                continue

            updated = False

            # domain 업데이트 (L2 형식 우선, fallback to flat)
            domain_val = None
            if has_domain_l2 and row.get("domain_l2", "").strip():
                domain_val = row["domain_l2"].strip()
            elif has_domain and row.get("domain", "").strip():
                domain_val = row["domain"].strip()

            if domain_val:
                # L2 유효성 검증
                if domain_val not in DOMAIN_L2_TO_L1:
                    result["invalid_domain"] += 1
                    logger.warning(
                        f"Invalid domain L2 '{domain_val}' "
                        f"for posting {posting_id}"
                    )
                elif skip_existing and posting.domain_l2:
                    pass
                else:
                    if not dry_run:
                        posting.domain_l2 = domain_val
                        posting.domain_l1 = DOMAIN_L2_TO_L1[domain_val]
                    updated = True

            # core_technologies 업데이트
            if has_tech and row.get("core_technologies", "").strip():
                tech_raw = row["core_technologies"].strip()
                try:
                    tech_list = json.loads(tech_raw)
                    if not isinstance(tech_list, list):
                        tech_list = [tech_list]
                except (json.JSONDecodeError, TypeError):
                    tech_list = [
                        t.strip() for t in tech_raw.split(",") if t.strip()
                    ]

                if skip_existing and posting.core_technologies:
                    pass
                else:
                    if not dry_run:
                        posting.core_technologies = tech_list
                    updated = True

            if updated:
                result["applied"] += 1
                batch_count += 1

                if not dry_run and batch_count >= BATCH_SIZE:
                    session.commit()
                    batch_count = 0
            else:
                result["skipped"] += 1

        # 남은 배치 커밋
        if not dry_run and batch_count > 0:
            session.commit()

    action = "Dry-run" if dry_run else "Imported"
    logger.info(
        f"{action}: applied={result['applied']}, "
        f"skipped={result['skipped']}, not_found={result['not_found']}, "
        f"invalid_domain={result['invalid_domain']}"
    )
    return result
