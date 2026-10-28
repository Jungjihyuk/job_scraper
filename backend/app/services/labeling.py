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
from app.models.job import ExperienceCategory, JobPosting

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

# 레거시 L2 → 표준 L2 매핑 (이전 라벨링 배치에서 사용된 비표준 표기)
LEGACY_L2_TO_STANDARD_L2 = {
    "커머스/리테일": "커머스",
    "콘텐츠/미디어": "미디어/엔터테인먼트",
    "모빌리티/자동차": "자동차/모빌리티",
    "금융/핀테크": "핀테크",
    "보안/사이버보안": "보안",
    "교육/에듀테크": "교육",
    "바이오/헬스케어": "디지털헬스",
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


def normalize_domain_l2(
    session: Session,
    dry_run: bool = False,
) -> dict:
    """레거시 domain_l2 값을 표준 L2로 교정하고 domain_l1도 함께 채운다.

    Returns:
        {"normalized": int, "total_legacy": int}
    """
    postings = (
        session.query(JobPosting)
        .filter(JobPosting.domain_l2.in_(LEGACY_L2_TO_STANDARD_L2.keys()))
        .all()
    )

    result = {"normalized": 0, "total_legacy": len(postings)}

    batch_count = 0
    for posting in postings:
        standard_l2 = LEGACY_L2_TO_STANDARD_L2[posting.domain_l2]
        l1 = DOMAIN_L2_TO_L1[standard_l2]

        if not dry_run:
            posting.domain_l2 = standard_l2
            posting.domain_l1 = l1
        result["normalized"] += 1
        batch_count += 1

        if not dry_run and batch_count >= BATCH_SIZE:
            session.commit()
            batch_count = 0

    if not dry_run and batch_count > 0:
        session.commit()

    action = "Dry-run" if dry_run else "Normalized"
    logger.info(
        f"{action} domain_l2: normalized={result['normalized']}, "
        f"total_legacy={result['total_legacy']}"
    )
    return result


def backfill_domain_l1(
    session: Session,
    dry_run: bool = False,
) -> dict:
    """domain_l2는 있지만 domain_l1이 비어있는 레코드를 백필.

    DOMAIN_L2_TO_L1 매핑을 사용하여 domain_l1을 자동으로 채운다.

    Returns:
        {"filled": int, "invalid": int, "total_missing": int}
    """
    postings = (
        session.query(JobPosting)
        .filter(
            JobPosting.domain_l2.isnot(None),
            JobPosting.domain_l2 != "",
            or_(
                JobPosting.domain_l1.is_(None),
                JobPosting.domain_l1 == "",
            ),
        )
        .all()
    )

    result = {"filled": 0, "invalid": 0, "total_missing": len(postings)}

    batch_count = 0
    for posting in postings:
        l1 = DOMAIN_L2_TO_L1.get(posting.domain_l2)
        if l1:
            if not dry_run:
                posting.domain_l1 = l1
            result["filled"] += 1
            batch_count += 1

            if not dry_run and batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0
        else:
            result["invalid"] += 1
            logger.warning(
                f"Unknown domain_l2 '{posting.domain_l2}' "
                f"for posting {posting.posting_id}"
            )

    if not dry_run and batch_count > 0:
        session.commit()

    action = "Dry-run" if dry_run else "Backfilled"
    logger.info(
        f"{action} domain_l1: filled={result['filled']}, "
        f"invalid={result['invalid']}, "
        f"total_missing={result['total_missing']}"
    )
    return result


def backfill_specialty(
    session: Session,
    dry_run: bool = False,
    overwrite: bool = False,
    limit: Optional[int] = None,
) -> dict:
    """기존 공고에 specialty_l1/l2를 백필.

    ContentAnalyzer.classify_specialty를 사용하여
    position + 본문(main_tasks, requirements, preferred)으로 직무를 분류한다.

    Args:
        session: DB 세션
        dry_run: True면 실제 변경 없이 결과만 확인
        overwrite: True면 이미 값이 있는 레코드도 재분류
        limit: 처리할 최대 건수

    Returns:
        {"classified": int, "unclassified": int, "total_target": int}
    """
    from app.pipeline.normalizers.content import ContentAnalyzer

    analyzer = ContentAnalyzer()
    if not analyzer._specialty_rules:
        logger.error("job_specialty.yaml을 로드할 수 없습니다")
        return {"classified": 0, "unclassified": 0, "total_target": 0}

    query = session.query(JobPosting)
    if not overwrite:
        query = query.filter(
            or_(
                JobPosting.specialty_l2.is_(None),
                JobPosting.specialty_l2 == "",
            )
        )

    query = query.order_by(JobPosting.id)
    if limit:
        query = query.limit(limit)

    postings = query.all()
    result = {"classified": 0, "unclassified": 0, "total_target": len(postings)}

    batch_count = 0
    for posting in postings:
        # 본문 조합
        parts = []
        if posting.main_tasks:
            parts.append(posting.main_tasks)
        if posting.requirements:
            parts.append(posting.requirements)
        if posting.preferred:
            parts.append(posting.preferred)
        body_text = " ".join(parts)

        position = posting.position or ""
        l1, l2 = analyzer.classify_specialty(position, body_text)

        if l2:
            if not dry_run:
                posting.specialty_l1 = l1
                posting.specialty_l2 = l2
            result["classified"] += 1
            batch_count += 1

            if not dry_run and batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0
        else:
            result["unclassified"] += 1

    if not dry_run and batch_count > 0:
        session.commit()

    action = "Dry-run" if dry_run else "Backfilled"
    logger.info(
        f"{action} specialty: classified={result['classified']}, "
        f"unclassified={result['unclassified']}, "
        f"total_target={result['total_target']}"
    )
    return result


def backfill_experience_category(
    session: Session,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> dict:
    """experience 텍스트는 있지만 experience_category_id가 NULL인 공고를 백필.

    ExperienceNormalizer로 경력 텍스트를 파싱한 뒤,
    ExperienceCategory를 찾거나 생성하여 연결한다.

    Returns:
        {"linked": int, "no_text": int, "failed": int, "total_target": int}
    """
    from app.pipeline.normalizers.experience import ExperienceNormalizer

    normalizer = ExperienceNormalizer()

    query = (
        session.query(JobPosting)
        .filter(JobPosting.experience_category_id.is_(None))
        .order_by(JobPosting.id)
    )
    if limit:
        query = query.limit(limit)

    postings = query.all()
    result = {
        "linked": 0,
        "no_text": 0,
        "failed": 0,
        "total_target": len(postings),
    }

    batch_count = 0
    for posting in postings:
        raw_exp = (posting.experience or "").strip()
        if not raw_exp:
            result["no_text"] += 1
            continue

        try:
            norm = normalizer.normalize_experience(raw_exp)

            # 기존 ExperienceCategory 조회
            exp_cat = (
                session.query(ExperienceCategory)
                .filter_by(raw_experience=norm.raw_experience)
                .first()
            )

            if not exp_cat:
                exp_cat = ExperienceCategory(
                    raw_experience=norm.raw_experience,
                    standardized_experience=norm.standardized_experience,
                    min_years=norm.min_years,
                    max_years=norm.max_years,
                    is_fresh_welcome=norm.is_fresh_welcome,
                    confidence=norm.confidence,
                    matching_method=norm.matching_method,
                    manual_review=norm.manual_review,
                )
                if not dry_run:
                    session.add(exp_cat)
                    session.flush()

            if not dry_run:
                posting.experience_category_id = exp_cat.experience_category_id

            result["linked"] += 1
            batch_count += 1

            if not dry_run and batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0

        except Exception as e:
            result["failed"] += 1
            logger.warning(
                f"Failed to normalize experience for posting "
                f"{posting.posting_id}: {e}"
            )

    if not dry_run and batch_count > 0:
        session.commit()

    action = "Dry-run" if dry_run else "Backfilled"
    logger.info(
        f"{action} experience_category: linked={result['linked']}, "
        f"no_text={result['no_text']}, failed={result['failed']}, "
        f"total_target={result['total_target']}"
    )
    return result
