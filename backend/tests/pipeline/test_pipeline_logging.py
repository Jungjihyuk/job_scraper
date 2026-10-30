"""FR-067: 수집 파이프라인 로깅 개선 테스트

_log_final_metrics, 수집 효율 비율, 필터링 건수 로깅 검증
"""

import pytest
from unittest.mock import patch, MagicMock

from app.pipeline.manager import PipelineManager
from app.pipeline.data_models import PipelineConfig, PipelineMetrics
from tests.conftest import make_job_posting, make_stage_result


def _make_manager(config: PipelineConfig) -> PipelineManager:
    with patch(
        "app.pipeline.manager.URLCollectorStage"
    ), patch(
        "app.pipeline.manager.URLValidatorStage"
    ), patch(
        "app.pipeline.manager.ContentScraperStage"
    ), patch(
        "app.pipeline.manager.JobNormalizerStage"
    ), patch(
        "app.pipeline.manager.DatabaseSaverStage"
    ):
        return PipelineManager(config)


class TestLogFinalMetrics:
    """최종 메트릭 요약 로깅"""

    def test_efficiency_calculation(self, default_config):
        """수집 효율 = 신규/전체 비율 계산"""
        mgr = _make_manager(default_config)
        mgr.total_collected_count = 100
        mgr.total_filtered_count = 60
        mgr.total_job_details_count = 40
        mgr.metrics = PipelineMetrics(
            valid_urls=35,
            invalid_urls=5,
            total_execution_time=120.5,
        )

        with patch.object(mgr.logger, "info") as mock_log:
            mgr._log_final_metrics()

        log_messages = [
            call.args[0] for call in mock_log.call_args_list
        ]

        # 핵심 메트릭이 로그에 포함되는지 확인
        assert any("100" in msg for msg in log_messages), \
            "URLs Collected 로그 누락"
        assert any("60" in msg for msg in log_messages), \
            "DB Filtered 로그 누락"
        assert any("40%" in msg or "40/100" in msg for msg in log_messages), \
            "신규 비율 로그 누락"
        assert any("35" in msg for msg in log_messages), \
            "Valid URLs 로그 누락"

    def test_zero_collected_shows_na(self, default_config):
        """수집 건수 0일 때 N/A 표시"""
        mgr = _make_manager(default_config)
        mgr.total_collected_count = 0
        mgr.total_filtered_count = 0
        mgr.total_job_details_count = 0
        mgr.metrics = PipelineMetrics()

        with patch.object(mgr.logger, "info") as mock_log:
            mgr._log_final_metrics()

        log_messages = [
            call.args[0] for call in mock_log.call_args_list
        ]
        assert any("N/A" in msg for msg in log_messages), \
            "0건일 때 N/A 미표시"


class TestFilterLogging:
    """DB 조기 필터링 시 로그 메시지 검증"""

    def test_filter_logs_counts(self, default_config):
        """필터링 시 기존/신규 건수가 로그에 남는지 확인"""
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = {"100", "101", "102"}

        posts = [
            make_job_posting(posting_id=str(i))
            for i in range(100, 106)
        ]

        with patch.object(mgr.logger, "info") as mock_log:
            result = mgr._filter_new_postings(posts)

        log_messages = [
            call.args[0] for call in mock_log.call_args_list
        ]
        # "6건 중 3건 기존, 3건 신규" 형태의 로그
        assert any("3건 기존" in msg for msg in log_messages)
        assert any("3건 신규" in msg for msg in log_messages)

    def test_no_log_when_no_duplicates(self, default_config):
        """중복이 없으면 필터링 로그 미출력"""
        mgr = _make_manager(default_config)
        mgr._existing_posting_ids = {"999"}

        posts = [make_job_posting(posting_id="100")]

        with patch.object(mgr.logger, "info") as mock_log:
            mgr._filter_new_postings(posts)

        log_messages = [
            call.args[0] for call in mock_log.call_args_list
        ]
        assert not any("기존" in msg for msg in log_messages)


class TestMetricsAccumulation:
    """PipelineMetrics 누적 테스트"""

    def test_add_stage_result(self):
        """stage result 추가 시 메트릭 누적"""
        metrics = PipelineMetrics()

        r1 = make_stage_result(
            stage_name="collector", urls_processed=10
        )
        r2 = make_stage_result(
            stage_name="validator", urls_processed=8
        )

        metrics.add_stage_result(r1)
        metrics.add_stage_result(r2)

        assert len(metrics.stage_results) == 2
        assert metrics.total_execution_time == 2  # 각 1초

    def test_success_rate_zero_total(self):
        """총 스크래핑 0건일 때 성공률 0.0"""
        metrics = PipelineMetrics()
        assert metrics.get_success_rate() == 0.0

    def test_success_rate_calculation(self):
        """성공률 계산"""
        metrics = PipelineMetrics(
            successful_scrapes=8, failed_scrapes=2
        )
        assert metrics.get_success_rate() == 80.0
