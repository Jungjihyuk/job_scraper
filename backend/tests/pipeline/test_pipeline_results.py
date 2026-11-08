"""파이프라인 실행 결과 집계 테스트

배치 상태와 건수가 스테이지의 실제 결과와 같은지 검증
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.data_models import (
    JobDetails,
    JobSaveResult,
    PipelineConfig,
)
from app.pipeline.manager import PipelineManager
from app.pipeline.stages.normalizer import JobNormalizerStage
from tests.conftest import (
    make_job_details,
    make_job_posting,
    make_stage_result,
    make_validated_url,
)


def _manager(max_scrolls: int = 1) -> PipelineManager:
    config = PipelineConfig(job="서버 개발자", max_scrolls=max_scrolls)
    with (
        patch("app.pipeline.manager.URLCollectorStage"),
        patch("app.pipeline.manager.URLValidatorStage"),
        patch("app.pipeline.manager.ContentScraperStage"),
        patch("app.pipeline.manager.JobNormalizerStage"),
        patch("app.pipeline.manager.DatabaseSaverStage"),
    ):
        mgr = PipelineManager(config)
    mgr._load_existing_posting_ids = MagicMock()
    mgr.cleanup = AsyncMock()
    saver = MagicMock()
    saver.batch_id = 1
    mgr.database_saver = saver
    mgr.local_file_saver = None
    mgr._validate_urls = AsyncMock(side_effect=_validate)
    mgr._normalize_jobs = AsyncMock(side_effect=_normalize)
    return mgr


async def _validate(posts):
    return make_stage_result(
        data=[make_validated_url(p.posting_id) for p in posts],
        urls_processed=len(posts),
    )


async def _normalize(details):
    return make_stage_result(data=details, urls_processed=len(details))


def _collect(*posting_ids: str, urls_failed: int = 0):
    return make_stage_result(
        data=[make_job_posting(posting_id=p) for p in posting_ids],
        urls_processed=len(posting_ids),
        urls_failed=urls_failed,
    )


def _scraped(*details: JobDetails):
    return make_stage_result(data=list(details), urls_processed=len(details))


def _failed(posting_id: str) -> JobDetails:
    details = make_job_details(posting_id=posting_id, success=False)
    details.error_message = "필수 칸 추출 실패"
    return details


def _wire_save(mgr: PipelineManager, *save_results: JobSaveResult) -> None:
    """URL 저장은 성공으로, 공고 저장은 주어진 결과로 돌려준다"""
    results = iter(save_results)

    async def execute(data):
        if isinstance(data[0], JobDetails):
            return make_stage_result(data=next(results))
        return make_stage_result(data=data, urls_processed=len(data))

    mgr.database_saver.execute = AsyncMock(side_effect=execute)


def _batch_call(mgr: PipelineManager):
    return mgr.database_saver.update_batch_status.call_args


class TestBatchResult:
    @pytest.mark.asyncio
    async def test_all_saved_is_completed(self):
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        assert metrics.batch_status == "completed"
        args = _batch_call(mgr)
        assert args.args == ("completed", 1)
        assert args.kwargs == {
            "collected": 1,
            "saved": 1,
            "failed": 0,
            "skipped": 0,
        }

    @pytest.mark.asyncio
    async def test_extraction_failure_is_counted_not_saved(self):
        """AC-1: 추출 실패는 실패 건수와 실패 횟수에 남고 캐시에 들어가지 않는다"""
        mgr = _manager()
        ok = make_job_details("1")
        bad = _failed("2")
        mgr._collect_urls = AsyncMock(return_value=_collect("1", "2"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok, bad))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        assert metrics.batch_status == "partial"
        assert metrics.saved_count == 1
        assert metrics.failed_count == 1
        assert "2" not in mgr._existing_posting_ids
        mgr.database_saver.record_failures.assert_any_call([bad])

    @pytest.mark.asyncio
    async def test_success_rate_is_real(self):
        """AC-12: 성공률이 실제 성공 건수를 처리 건수로 나눈 값이다"""
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(
            return_value=_collect("1", "2", "3", "4")
        )
        mgr._scrape_content = AsyncMock(
            return_value=_scraped(ok, _failed("2"), _failed("3"), _failed("4"))
        )
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        assert metrics.get_success_rate() == 25.0

    @pytest.mark.asyncio
    async def test_save_failure_is_partial_and_not_cached(self):
        """AC-4: 저장 실패는 partial이고 저장 건수와 캐시에 들어가지 않는다"""
        mgr = _manager()
        ok = make_job_details("1")
        lost = make_job_details("2")
        mgr._collect_urls = AsyncMock(return_value=_collect("1", "2"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok, lost))
        _wire_save(mgr, JobSaveResult(saved=[ok], failed=[lost]))

        metrics = await mgr.run()

        assert metrics.batch_status == "partial"
        assert metrics.saved_count == 1
        assert metrics.failed_count == 1
        assert mgr._existing_posting_ids == {"1"}
        mgr.database_saver.record_failures.assert_called_with([lost])

    @pytest.mark.asyncio
    async def test_save_stage_failure_fails_all_successes(self):
        """AC-5: 저장 스테이지가 통째로 실패하면 저장 0건이라 failed다"""
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))

        async def execute(data):
            if isinstance(data[0], JobDetails):
                result = make_stage_result(success=False)
                result.error_message = "DB 끊김"
                return result
            return make_stage_result(data=data, urls_processed=len(data))

        mgr.database_saver.execute = AsyncMock(side_effect=execute)

        metrics = await mgr.run()

        assert metrics.batch_status == "failed"
        assert metrics.failed_count == 1
        assert "DB 끊김" in ok.error_message
        assert mgr._existing_posting_ids == set()

    @pytest.mark.asyncio
    async def test_all_extraction_failed_is_failed(self):
        """AC-5: 처리한 공고가 있는데 저장 0건이면 failed다"""
        mgr = _manager()
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(_failed("1")))
        _wire_save(mgr)

        metrics = await mgr.run()

        assert metrics.batch_status == "failed"
        assert metrics.failed_count == 1

    @pytest.mark.asyncio
    async def test_scrape_stage_failure_counts_every_url(self):
        mgr = _manager()
        mgr._collect_urls = AsyncMock(return_value=_collect("1", "2"))
        failure = make_stage_result(success=False)
        failure.error_message = "브라우저 없음"
        mgr._scrape_content = AsyncMock(return_value=failure)
        _wire_save(mgr)

        metrics = await mgr.run()

        assert metrics.batch_status == "failed"
        assert metrics.failed_count == 2
        recorded = mgr.database_saver.record_failures.call_args.args[0]
        assert [d.error_message for d in recorded] == ["브라우저 없음"] * 2

    @pytest.mark.asyncio
    async def test_no_new_postings_is_completed(self):
        """AC-10: 새 공고가 없으면 completed이고 저장 0건이다"""
        mgr = _manager()
        mgr._existing_posting_ids = {"1", "2"}
        mgr._collect_urls = AsyncMock(return_value=_collect("1", "2"))
        mgr._scrape_content = AsyncMock()

        metrics = await mgr.run()

        assert metrics.batch_status == "completed"
        assert metrics.total_urls_collected == 2
        assert _batch_call(mgr).kwargs["collected"] == 2
        mgr._scrape_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_stage_failure_with_nothing_saved_is_failed(self):
        mgr = _manager()
        mgr._collect_urls = AsyncMock(
            return_value=make_stage_result(success=False, urls_processed=0)
        )

        metrics = await mgr.run()

        assert metrics.batch_status == "failed"

    @pytest.mark.asyncio
    async def test_collect_stage_failure_after_saving_is_partial(self):
        mgr = _manager(max_scrolls=2)
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(
            side_effect=[
                _collect("1"),
                make_stage_result(success=False, urls_processed=0),
            ]
        )
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        assert metrics.batch_status == "partial"

    @pytest.mark.asyncio
    async def test_no_card_readable_is_failed(self):
        """카드가 있는데 하나도 읽지 못하면 신규 0건이 아니라 failed다"""
        mgr = _manager()
        mgr._collect_urls = AsyncMock(
            return_value=_collect(urls_failed=5)
        )

        metrics = await mgr.run()

        assert metrics.batch_status == "failed"
        assert metrics.failed_cards == 5

    @pytest.mark.asyncio
    async def test_some_failed_cards_do_not_change_status(self):
        """AC-8: 일부 카드 실패는 메트릭에만 남고 상태를 바꾸지 않는다"""
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(
            return_value=_collect("1", urls_failed=2)
        )
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        assert metrics.batch_status == "completed"
        assert metrics.failed_cards == 2

    @pytest.mark.asyncio
    async def test_exception_marks_failed_with_counts(self):
        mgr = _manager(max_scrolls=2)
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(
            side_effect=[_collect("1"), RuntimeError("boom")]
        )
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        with pytest.raises(RuntimeError):
            await mgr.run()

        assert mgr.metrics.batch_status == "failed"
        args = _batch_call(mgr)
        assert args.args[0] == "failed"
        assert args.kwargs["saved"] == 1


class TestMultiCycleCounts:
    @pytest.mark.asyncio
    async def test_counts_equal_real_processing(self):
        """AC-11: 사이클을 거듭해도 건수가 실제 처리 건수와 같다"""
        mgr = _manager(max_scrolls=3)
        first = make_job_details("1")
        second = make_job_details("2")
        mgr._collect_urls = AsyncMock(
            side_effect=[
                _collect("1", "x"),
                _collect("2", "y"),
                _collect("known"),
            ]
        )
        mgr._existing_posting_ids = {"known"}
        mgr._scrape_content = AsyncMock(
            side_effect=[
                _scraped(first, _failed("x")),
                _scraped(second, _failed("y")),
            ]
        )
        _wire_save(
            mgr,
            JobSaveResult(saved=[first]),
            JobSaveResult(saved=[second]),
        )

        metrics = await mgr.run()

        assert metrics.total_urls_collected == 5
        assert metrics.valid_urls == 4
        assert metrics.successful_scrapes == 2
        assert metrics.failed_scrapes == 2
        assert metrics.saved_count == 2
        assert metrics.failed_count == 2
        assert _batch_call(mgr).kwargs == {
            "collected": 5,
            "saved": 2,
            "failed": 2,
            "skipped": 0,
        }


class TestFileSaveFailures:
    @pytest.mark.asyncio
    async def test_failures_reach_metrics(self):
        """AC-9: 파일 저장 실패 건수가 메트릭에 남고 상태는 바꾸지 않는다"""
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))
        mgr.local_file_saver = MagicMock()
        mgr.local_file_saver.execute = AsyncMock(
            return_value=make_stage_result(urls_processed=0, urls_failed=1)
        )

        metrics = await mgr.run()

        assert metrics.file_save_failures == 1
        assert metrics.batch_status == "completed"

    @pytest.mark.asyncio
    async def test_exception_counts_all_items(self):
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))
        mgr.local_file_saver = MagicMock()
        mgr.local_file_saver.execute = AsyncMock(
            side_effect=OSError("디스크 가득")
        )

        metrics = await mgr.run()

        assert metrics.file_save_failures == 1


class TestRetryLimit:
    @pytest.mark.asyncio
    async def test_exhausted_url_is_not_scraped_and_counted(self):
        """AC-18: 제한에 걸린 공고는 시도하지 않고 건너뛴 건수에 세어진다"""
        mgr = _manager()
        ok = make_job_details("2")
        mgr._exhausted_urls = {make_job_posting(posting_id="1").full_url}
        mgr._collect_urls = AsyncMock(return_value=_collect("1", "2"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        scraped = mgr._scrape_content.call_args.args[0]
        assert [u.job_url.posting_id for u in scraped] == ["2"]
        assert metrics.skipped_count == 1
        assert metrics.batch_status == "completed"
        assert _batch_call(mgr).kwargs["skipped"] == 1

    @pytest.mark.asyncio
    async def test_only_exhausted_postings_end_completed(self):
        mgr = _manager()
        mgr._exhausted_urls = {make_job_posting(posting_id="1").full_url}
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._validate_urls = AsyncMock()

        metrics = await mgr.run()

        mgr._validate_urls.assert_not_called()
        assert metrics.skipped_count == 1
        assert metrics.batch_status == "completed"

    @pytest.mark.asyncio
    async def test_existing_posting_is_not_counted_as_skipped(self):
        mgr = _manager()
        posting = make_job_posting(posting_id="1")
        mgr._existing_posting_ids = {"1"}
        mgr._exhausted_urls = {posting.full_url}
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))

        metrics = await mgr.run()

        assert metrics.skipped_count == 0


class TestNormalizationFailed:
    @pytest.mark.asyncio
    async def test_failed_stage_marks_and_still_saves(self):
        """AC-7: 정규화 스테이지가 실패해도 표시를 남기고 저장한다"""
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        mgr._normalize_jobs = AsyncMock(
            return_value=make_stage_result(success=False)
        )
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        metrics = await mgr.run()

        assert ok.normalization_failed is True
        assert metrics.saved_count == 1
        assert metrics.batch_status == "completed"

    @pytest.mark.asyncio
    async def test_exception_marks_too(self):
        mgr = _manager()
        ok = make_job_details("1")
        mgr._collect_urls = AsyncMock(return_value=_collect("1"))
        mgr._scrape_content = AsyncMock(return_value=_scraped(ok))
        mgr._normalize_jobs = AsyncMock(side_effect=RuntimeError("boom"))
        _wire_save(mgr, JobSaveResult(saved=[ok]))

        await mgr.run()

        assert ok.normalization_failed is True

    @pytest.mark.asyncio
    async def test_item_failure_marks_only_that_item(self):
        """AC-7: 항목 하나의 정규화 실패는 그 공고에만 표시된다"""
        stage = JobNormalizerStage()
        good = make_job_details("1")
        bad = make_job_details("2")

        def analyze(details):
            if details is bad:
                raise ValueError("분석 실패")
            return details

        stage._analyze_content = analyze

        result = await stage.process([good, bad])

        assert result == [good, bad]
        assert good.normalization_failed is False
        assert bad.normalization_failed is True
