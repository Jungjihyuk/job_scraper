"""정리 명령을 실제 PostgreSQL에 돌리는 테스트

임시 DB를 DB_* 환경변수로 가리키고 RUN_DB_TESTS=1을 줄 때만 실행한다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.config import db_config
from app.core.database import db_manager
from app.models import (
    Company,
    JobCategory,
    JobPosting,
    Location,
    ScrapedUrl,
    ScrapingBatch,
)
from app.models.base import Base
from app.pipeline.diagnostics.cleanup_failed_postings import (
    CleanupCounts,
    apply_cleanup,
    count_targets,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="RUN_DB_TESTS=1일 때만 실행"
)


@pytest.fixture
def seeded():
    """종류별 정리 대상과 멀쩡한 공고가 있는 DB"""
    assert db_config.database != "job_scraper_db"
    db_manager.initialize()
    Base.metadata.create_all(db_manager.engine)
    with db_manager.get_session() as session:
        session.execute(
            text(
                "TRUNCATE job_posting, scraped_urls, scraping_tasks, "
                "scraping_batches, locations, companies, job_categories "
                "RESTART IDENTITY CASCADE"
            )
        )
        company = Company(company_name="회사")
        category = JobCategory(
            job_category="개발", job_field="서버", scraper_type="wanted"
        )
        real = Location(location="서울 강남구", location_detail="테헤란로 1")
        no_detail = Location(
            location="서울 강남구", location_detail="No work place"
        )
        no_name = Location(location="No location", location_detail="판교역")
        both = Location(location="No location", location_detail="No work place")
        batch = ScrapingBatch(
            batch_name="b", scraper_type="wanted", status="completed"
        )
        session.add_all([company, category, real, no_detail, no_name, both])
        session.add(batch)
        session.flush()

        def posting(posting_id: str, location: Location, **fields) -> None:
            values = {
                "position": "제목",
                "main_tasks": "업무",
                "requirements": "요건",
                **fields,
            }
            session.add(
                JobPosting(
                    posting_id=posting_id,
                    job_category_id=category.job_category_id,
                    company_id=company.company_id,
                    location_id=location.location_id,
                    **values,
                )
            )

        posting("ok", real)
        posting("no-title", real, position="No title")
        posting(
            "no-body",
            real,
            main_tasks="Extraction failed",
            requirements="",
        )
        posting(
            "fake",
            no_detail,
            experience="No experience",
            preferred="Extraction failed",
        )
        posting("one-body", no_name, main_tasks=None)
        posting("both", both)
        session.add_all(
            [
                ScrapedUrl(
                    batch_id=batch.id,
                    url=f"https://x/{n}",
                    url_hash=f"h{n}",
                    status="failed",
                    retry_count=n,
                )
                for n in (2, 3, 4)
            ]
        )
        session.commit()


def _snapshot(session) -> dict:
    return {
        "postings": sorted(
            row.posting_id for row in session.query(JobPosting.posting_id)
        ),
        "locations": sorted(
            (row.location, row.location_detail or "")
            for row in session.query(Location)
        ),
        "retries": sorted(row.retry_count for row in session.query(ScrapedUrl)),
    }


def test_preview_counts_by_kind_and_changes_nothing(seeded):
    """AC-16: 종류별 건수를 내고 DB는 바뀌지 않는다"""
    with db_manager.get_session() as session:
        before = _snapshot(session)
        counts = count_targets(session)
        session.commit()

    assert counts == CleanupCounts(
        empty_postings=2,
        fake_value_postings=1,
        fake_locations=3,
        postings_on_fake_locations=3,
        retry_limited_urls=2,
    )
    with db_manager.get_session() as session:
        assert _snapshot(session) == before


def test_apply_cleans_every_kind(seeded, tmp_path):
    """AC-17 · AC-19: 빈 공고 삭제, 가짜 값 NULL, 지역 정리, 제한 초기화"""
    with db_manager.get_session() as session:
        backup = apply_cleanup(session, tmp_path)
        session.commit()

    with db_manager.get_session() as session:
        snapshot = _snapshot(session)
        assert snapshot["postings"] == ["both", "fake", "ok", "one-body"]
        assert snapshot["retries"] == [0, 0, 2]
        assert snapshot["locations"] == [
            ("미상", ""),
            ("미상", "판교역"),
            ("서울 강남구", ""),
            ("서울 강남구", "테헤란로 1"),
        ]

        def location_of(posting_id: str) -> tuple:
            posting = (
                session.query(JobPosting).filter_by(posting_id=posting_id).one()
            )
            location = session.get(Location, posting.location_id)
            return location.location, location.location_detail

        assert location_of("both") == ("미상", None)
        assert location_of("fake") == ("서울 강남구", None)
        assert location_of("one-body") == ("미상", "판교역")

        fake = session.query(JobPosting).filter_by(posting_id="fake").one()
        assert fake.experience is None
        assert fake.preferred is None
        assert fake.main_tasks == "업무"

        assert count_targets(session) == CleanupCounts(0, 0, 0, 0, 0)

    deleted = json.loads(backup.read_text(encoding="utf-8"))
    assert sorted(row["posting_id"] for row in deleted) == [
        "no-body",
        "no-title",
    ]


def test_failure_rolls_everything_back(seeded, tmp_path, monkeypatch):
    """한 트랜잭션이라 중간에 실패하면 아무것도 바뀌지 않는다"""
    with db_manager.get_session() as session:
        before = _snapshot(session)
        session.commit()

    def boom(*_args):
        raise RuntimeError("중간 실패")

    monkeypatch.setattr(
        "app.pipeline.diagnostics.cleanup_failed_postings."
        "_replacement_location",
        boom,
    )
    with (
        pytest.raises(RuntimeError),
        db_manager.get_session() as session,
    ):
        apply_cleanup(session, tmp_path)

    with db_manager.get_session() as session:
        assert _snapshot(session) == before


def test_command_preview_prints_counts(seeded):
    """AC-16: 명령을 인자 없이 실행하면 건수만 출력한다"""
    script = (
        Path(__file__).resolve().parents[2]
        / "app/pipeline/diagnostics/cleanup_failed_postings.py"
    )
    done = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "empty_postings: 2" in done.stdout
    assert "Nothing changed" in done.stdout
    with db_manager.get_session() as session:
        assert session.query(JobPosting).count() == 6
