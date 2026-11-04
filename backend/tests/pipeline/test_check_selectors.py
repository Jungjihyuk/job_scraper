"""check_selectors의 칸 판정 로직 테스트."""

import pytest

from app.pipeline.diagnostics.check_selectors import (
    REQUIRED_FIELDS,
    PostingCheck,
    has_required_failure,
    is_extracted,
    missing_fields,
)


@pytest.mark.parametrize(
    "value",
    ["No title", "No location", "Extraction failed", "", "   ", None, []],
)
def test_is_extracted_rejects_empty_and_placeholder(value):
    assert is_extracted(value) is False


@pytest.mark.parametrize("value", ["백엔드 엔지니어", "상시채용", ["식대지원"]])
def test_is_extracted_accepts_real_value(value):
    assert is_extracted(value) is True


def test_missing_fields_lists_only_unread_fields():
    check = PostingCheck(
        "u", {"title": "제목", "main_tasks": "Extraction failed"}
    )

    assert missing_fields(check, REQUIRED_FIELDS) == [
        "main_tasks",
        "requirements",
    ]


def test_has_required_failure_when_one_posting_lacks_required_field():
    good = PostingCheck(
        "a", {"title": "t", "main_tasks": "m", "requirements": "r"}
    )
    bad = PostingCheck(
        "b", {"title": "No title", "main_tasks": "m", "requirements": "r"}
    )

    assert has_required_failure([good]) is False
    assert has_required_failure([good, bad]) is True


def test_optional_field_does_not_fail_required_check():
    check = PostingCheck(
        "a", {"title": "t", "main_tasks": "m", "requirements": "r", "tags": []}
    )

    assert has_required_failure([check]) is False
