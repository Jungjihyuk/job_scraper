"""실행 결과 건수와 정규화 실패 표시 열을 추가한다.

ADR-002 선택지 A. 실패 횟수는 기존 retry_count 열을 쓰므로 더하지 않는다.

Revision ID: 7c2e91ab4d10
Revises: 5426883d0c04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c2e91ab4d10"
down_revision: str | Sequence[str] | None = "5426883d0c04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BATCH_COUNT_COLUMNS = (
    "collected_count",
    "saved_count",
    "failed_count",
    "skipped_count",
)


def upgrade() -> None:
    """열 5개를 기본값과 함께 추가한다."""
    op.add_column(
        "job_posting",
        sa.Column(
            "normalization_failed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    for name in BATCH_COUNT_COLUMNS:
        op.add_column(
            "scraping_batches",
            sa.Column(name, sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    """추가한 열 5개를 지운다."""
    for name in BATCH_COUNT_COLUMNS:
        op.drop_column("scraping_batches", name)
    op.drop_column("job_posting", "normalization_failed")
