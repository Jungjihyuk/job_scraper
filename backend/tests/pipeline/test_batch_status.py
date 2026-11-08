"""decide_batch_status 단위 테스트"""

import pytest

from app.pipeline.manager import decide_batch_status


@pytest.mark.parametrize(
    ("saved", "failed", "stage_error", "expected"),
    [
        (10, 0, False, "completed"),
        (0, 0, False, "completed"),  # AC-10: 신규 0건
        (10, 3, False, "partial"),  # AC-4
        (10, 0, True, "partial"),
        (10, 3, True, "partial"),
        (0, 3, False, "failed"),  # AC-5
        (0, 0, True, "failed"),
        (0, 3, True, "failed"),
    ],
)
def test_decide_batch_status(saved, failed, stage_error, expected):
    assert decide_batch_status(saved, failed, stage_error) == expected
