"""
Taxonomy 기반 재라벨링 서비스 (FR-058).

taxonomy 버전이 변경되었을 때 기존 데이터를 새 기준으로 재분류.
키워드 기반 자동 재분류와 수동 검수 대상 분리를 수행한다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.logging import create_development_logger
from app.models.job import JobPosting
from app.pipeline.normalizers.content import ContentAnalyzer
from app.services.taxonomy import get_taxonomy_manager

logger = create_development_logger(__name__)

BATCH_SIZE = 200
AUTO_CONFIDENCE_THRESHOLD = 0.8


@dataclass
class RelabelResult:
    """재라벨링 결과 요약."""

    total_target: int = 0
    unchanged: int = 0
    auto_relabeled: int = 0
    manual_review: int = 0
    errors: int = 0
    changes: List[dict] = field(default_factory=list)


def count_relabel_targets(
    session: Session,
    target: Optional[str] = None,
) -> Dict[str, int]:
    """재라벨링 대상 건수를 taxonomy별로 반환.

    Args:
        session: DB 세션
        target: 'domain', 'technology', None(전체)

    Returns:
        {"domain": N, "technology": N, "total": N}
    """
    mgr = get_taxonomy_manager()
    domain_ver = mgr.get_version("domain")
    tech_ver = mgr.get_version("technology")

    counts = {}

    if target in (None, "domain"):
        q = session.query(JobPosting).filter(
            or_(
                JobPosting.taxonomy_version.is_(None),
                JobPosting.taxonomy_version < domain_ver,
            ),
            # domain_l1이 있는 레코드만 (분류된 적 있는 것)
            JobPosting.domain_l1.isnot(None),
        )
        counts["domain"] = q.count()

    if target in (None, "technology"):
        q = session.query(JobPosting).filter(
            or_(
                JobPosting.taxonomy_version.is_(None),
                JobPosting.taxonomy_version < tech_ver,
            ),
            JobPosting.core_technologies.isnot(None),
        )
        counts["technology"] = q.count()

    counts["total"] = session.query(JobPosting).filter(
        or_(
            JobPosting.taxonomy_version.is_(None),
            JobPosting.taxonomy_version < domain_ver,
        )
    ).count()

    return counts


def relabel_postings(
    session: Session,
    target: Optional[str] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> RelabelResult:
    """기존 공고를 새 taxonomy 기준으로 재분류.

    Args:
        session: DB 세션
        target: 'domain', 'technology', None(전체)
        dry_run: True면 실제 변경 없이 결과만 반환
        limit: 처리할 최대 건수

    Returns:
        RelabelResult: 재라벨링 결과 요약
    """
    mgr = get_taxonomy_manager()
    current_version = mgr.get_version("domain")
    analyzer = ContentAnalyzer()
    result = RelabelResult()

    # 대상 조회: taxonomy_version이 없거나 현재보다 낮은 레코드
    query = session.query(JobPosting).filter(
        or_(
            JobPosting.taxonomy_version.is_(None),
            JobPosting.taxonomy_version < current_version,
        )
    ).order_by(JobPosting.id)

    if limit:
        query = query.limit(limit)

    postings = query.all()
    result.total_target = len(postings)

    if not postings:
        return result

    batch_count = 0

    for posting in postings:
        try:
            _relabel_single(
                posting=posting,
                analyzer=analyzer,
                target=target,
                current_version=current_version,
                result=result,
                dry_run=dry_run,
                session=session,
            )
            batch_count += 1

            if not dry_run and batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0

        except Exception as e:
            result.errors += 1
            logger.error(
                f"Relabel error for posting {posting.posting_id}: {e}"
            )

    # 수동 검토 대상 staging 테이블에 기록
    if result.changes:
        manual_changes = [
            c for c in result.changes if c["action"] == "manual_review"
        ]
        if manual_changes and not dry_run:
            _insert_to_staging(session, manual_changes)

    if not dry_run and batch_count > 0:
        session.commit()

    return result


def _relabel_single(
    posting: JobPosting,
    analyzer: ContentAnalyzer,
    target: Optional[str],
    current_version: str,
    result: RelabelResult,
    dry_run: bool,
    session: Session,
) -> None:
    """단일 공고 재라벨링 처리."""
    # 본문 텍스트 조합
    parts = []
    for field_name in ("main_tasks", "requirements", "preferred"):
        val = getattr(posting, field_name, None)
        if val:
            parts.append(val)

    body_text = " ".join(parts)

    # 본문이 없으면 버전만 갱신
    if not body_text.strip():
        if not dry_run:
            posting.taxonomy_version = current_version
        result.unchanged += 1
        return

    analysis = analyzer.analyze(body_text)

    domain_changed = False
    tech_changed = False

    # 도메인 재분류
    if target in (None, "domain"):
        old_domain = posting.domain_l1
        new_domain = analysis.domain

        if new_domain and new_domain != old_domain:
            if analysis.domain_confidence >= AUTO_CONFIDENCE_THRESHOLD:
                domain_changed = True
                if not dry_run:
                    posting.domain_l1 = new_domain
                result.changes.append({
                    "posting_id": posting.posting_id,
                    "field": "domain_l1",
                    "old": old_domain,
                    "new": new_domain,
                    "confidence": analysis.domain_confidence,
                    "action": "auto_relabel",
                })
            else:
                result.changes.append({
                    "posting_id": posting.posting_id,
                    "field": "domain_l1",
                    "old": old_domain,
                    "new": new_domain,
                    "confidence": analysis.domain_confidence,
                    "action": "manual_review",
                })

    # 기술 재분류
    if target in (None, "technology"):
        old_tech = posting.core_technologies or []
        new_tech = analysis.core_technologies or []

        if sorted(new_tech) != sorted(old_tech):
            tech_changed = True
            if not dry_run:
                posting.core_technologies = new_tech
            result.changes.append({
                "posting_id": posting.posting_id,
                "field": "core_technologies",
                "old": old_tech,
                "new": new_tech,
                "confidence": 1.0,
                "action": "auto_relabel",
            })

    # 결과 분류
    has_manual = any(
        c["posting_id"] == posting.posting_id
        and c["action"] == "manual_review"
        for c in result.changes
    )

    if has_manual:
        result.manual_review += 1
        # 수동 검토 대상은 버전 갱신하지 않음
    elif domain_changed or tech_changed:
        result.auto_relabeled += 1
        if not dry_run:
            posting.taxonomy_version = current_version
    else:
        result.unchanged += 1
        if not dry_run:
            posting.taxonomy_version = current_version


def _insert_to_staging(
    session: Session,
    changes: List[dict],
) -> None:
    """수동 검토 대상을 domain_review_staging에 기록."""
    mgr = get_taxonomy_manager()
    version = mgr.get_version("domain")

    for change in changes:
        if change["field"] != "domain_l1":
            continue

        try:
            session.execute(
                text("""
                    INSERT INTO domain_review_staging
                        (posting_id, reviewed_domain,
                         ai_predicted_domain, reviewer_note,
                         annotation_id, reviewed_at, status,
                         taxonomy_version)
                    VALUES
                        (:posting_id, :reviewed_domain,
                         :ai_predicted_domain, :reviewer_note,
                         0, NOW(), 'pending',
                         :taxonomy_version)
                    ON CONFLICT (posting_id, annotation_id) DO UPDATE SET
                        ai_predicted_domain = EXCLUDED.ai_predicted_domain,
                        reviewer_note = EXCLUDED.reviewer_note,
                        status = 'pending',
                        taxonomy_version = EXCLUDED.taxonomy_version
                """),
                {
                    "posting_id": change["posting_id"],
                    "reviewed_domain": change["old"] or "",
                    "ai_predicted_domain": change["new"],
                    "reviewer_note": (
                        f"Auto-relabel candidate "
                        f"(confidence: {change['confidence']:.2f})"
                    ),
                    "taxonomy_version": version,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to insert staging for "
                f"{change['posting_id']}: {e}"
            )
