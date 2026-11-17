#!/usr/bin/env python3
"""이미 DB에 쌓인 빈 공고와 가짜 값, 실패 횟수 제한을 정리한다.

기본은 건수만 출력하는 미리 보기이고, `--apply`를 줘야 한 트랜잭션으로 고친다.
공고를 새로 수집하지는 않는다. 지운 공고는 다음 실행에서 다시 수집된다.

Usage:
    uv run python app/pipeline/diagnostics/cleanup_failed_postings.py
    uv run python app/pipeline/diagnostics/cleanup_failed_postings.py --apply
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, inspect, or_, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.core.database import db_manager
from app.models import JobPosting, Location, ScrapedUrl
from app.pipeline.manager import MAX_SCRAPE_FAILURES

UNKNOWN_LOCATION = "미상"
FAKE_TITLE = "No title"
FAKE_BODY = "Extraction failed"
FAKE_LOCATION_VALUES = ("No location", "No work place")
FAKE_POSTING_VALUES = {
    "experience": "No experience",
    "position_detail": "No position detail",
    "main_tasks": FAKE_BODY,
    "requirements": FAKE_BODY,
    "preferred": FAKE_BODY,
    "benefits": FAKE_BODY,
    "hiring_process": FAKE_BODY,
}
BACKUP_DIR = Path(__file__).resolve().parents[3] / "logs"


@dataclass
class CleanupCounts:
    """종류별 정리 대상 건수."""

    empty_postings: int
    fake_value_postings: int
    fake_locations: int
    postings_on_fake_locations: int
    retry_limited_urls: int


def _is_blank(column: ColumnElement, fake_value: str) -> ColumnElement:
    """칸이 비었거나 대체 문자열인 조건을 만든다.

    Args:
        column: 확인할 열.
        fake_value: 이 칸에 들어갔던 대체 문자열.

    Returns:
        SQL 조건.
    """
    return or_(column.is_(None), func.trim(column) == "", column == fake_value)


def _empty_posting_condition() -> ColumnElement:
    """제목이 없거나 본문 두 칸이 모두 없는 공고의 조건을 만든다.

    Returns:
        SQL 조건.
    """
    return or_(
        _is_blank(JobPosting.position, FAKE_TITLE),
        _is_blank(JobPosting.main_tasks, FAKE_BODY)
        & _is_blank(JobPosting.requirements, FAKE_BODY),
    )


def _fake_location_condition() -> ColumnElement:
    """이름이나 상세에 대체 문자열이 있는 지역의 조건을 만든다.

    Returns:
        SQL 조건.
    """
    return or_(
        Location.location.in_(FAKE_LOCATION_VALUES),
        Location.location_detail.in_(FAKE_LOCATION_VALUES),
    )


def count_targets(session: Session) -> CleanupCounts:
    """정리 대상 건수를 센다. DB는 바꾸지 않는다.

    Args:
        session: DB 세션.

    Returns:
        종류별 건수. 지울 빈 공고는 다른 종류의 건수에 넣지 않는다.
    """
    not_empty = ~_empty_posting_condition()
    has_fake_value = or_(
        *(
            getattr(JobPosting, name) == value
            for name, value in FAKE_POSTING_VALUES.items()
        )
    )
    fake_location_ids = session.query(Location.location_id).filter(
        _fake_location_condition()
    )
    return CleanupCounts(
        empty_postings=session.query(JobPosting)
        .filter(_empty_posting_condition())
        .count(),
        fake_value_postings=session.query(JobPosting)
        .filter(not_empty, has_fake_value)
        .count(),
        fake_locations=fake_location_ids.count(),
        postings_on_fake_locations=session.query(JobPosting)
        .filter(not_empty, JobPosting.location_id.in_(fake_location_ids))
        .count(),
        retry_limited_urls=session.query(ScrapedUrl)
        .filter(ScrapedUrl.retry_count >= MAX_SCRAPE_FAILURES)
        .count(),
    )


def _backup_postings(postings: list[JobPosting], backup_dir: Path) -> Path:
    """지울 공고를 JSON으로 남긴다.

    Args:
        postings: 지울 공고.
        backup_dir: 저장할 폴더.

    Returns:
        만든 파일의 경로.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = backup_dir / f"cleanup_failed_postings_{timestamp}.json"
    rows = [
        {
            column.key: getattr(posting, column.key)
            for column in inspect(JobPosting).column_attrs
        }
        for posting in postings
    ]
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def _replacement_location(session: Session, fake: Location) -> Location:
    """가짜 지역의 공고를 옮길 지역을 찾거나 만든다.

    Args:
        session: DB 세션.
        fake: 대체 문자열이 들어간 지역.

    Returns:
        대체 문자열을 뺀 지역. 이름이 없으면 `미상`이다.
    """
    name = (
        UNKNOWN_LOCATION
        if fake.location in FAKE_LOCATION_VALUES
        else fake.location
    )
    detail = (
        None
        if fake.location_detail in FAKE_LOCATION_VALUES
        else fake.location_detail
    )
    location = (
        session.query(Location)
        .filter_by(location=name, location_detail=detail)
        .first()
    )
    if location is None:
        location = Location(
            location=name,
            location_detail=detail,
            region=name.split(" ", 1)[0],
        )
        session.add(location)
        session.flush()
    return location


def apply_cleanup(session: Session, backup_dir: Path = BACKUP_DIR) -> Path:
    """정리를 적용한다. 커밋은 호출한 쪽이 한다.

    Args:
        session: DB 세션.
        backup_dir: 지운 공고의 JSON을 저장할 폴더.

    Returns:
        지운 공고를 남긴 JSON 파일의 경로.
    """
    empty_postings = (
        session.query(JobPosting).filter(_empty_posting_condition()).all()
    )
    backup_path = _backup_postings(empty_postings, backup_dir)
    for posting in empty_postings:
        session.delete(posting)
    session.flush()

    for name, value in FAKE_POSTING_VALUES.items():
        column = getattr(JobPosting, name)
        session.execute(
            update(JobPosting).where(column == value).values({name: None})
        )

    for fake in (
        session.query(Location).filter(_fake_location_condition()).all()
    ):
        replacement = _replacement_location(session, fake)
        session.execute(
            update(JobPosting)
            .where(JobPosting.location_id == fake.location_id)
            .values(location_id=replacement.location_id)
        )
        session.delete(fake)
    session.flush()

    session.execute(
        update(ScrapedUrl)
        .where(ScrapedUrl.retry_count >= MAX_SCRAPE_FAILURES)
        .values(retry_count=0)
    )
    return backup_path


def print_counts(counts: CleanupCounts) -> None:
    """종류별 건수를 출력한다.

    Args:
        counts: 정리 대상 건수.
    """
    for name, count in asdict(counts).items():
        print(f"  {name}: {count}")


def main() -> None:
    """명령줄 인자를 읽어 미리 보기나 적용을 실행한다."""
    parser = argparse.ArgumentParser(
        description="Clean up empty postings, fake values and retry limits"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Change the database (default: preview only)",
    )
    args = parser.parse_args()

    if not db_manager.initialize():
        sys.exit(1)

    with db_manager.get_session() as session:
        print("Cleanup targets:")
        print_counts(count_targets(session))
        if not args.apply:
            print("Preview only. Nothing changed. Use --apply to change.")
            return

        backup_path = apply_cleanup(session)
        session.commit()
        print(f"Applied. Deleted postings saved to: {backup_path}")
        print("Remaining targets:")
        print_counts(count_targets(session))


if __name__ == "__main__":
    main()
