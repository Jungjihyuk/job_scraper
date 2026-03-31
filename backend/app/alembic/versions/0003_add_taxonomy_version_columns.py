"""add taxonomy_version columns to staging tables (FR-057)

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # domain_review_staging 테이블 생성 (없을 수 있음)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_review_staging (
            id SERIAL PRIMARY KEY,
            posting_id VARCHAR(100) NOT NULL,
            reviewed_domain VARCHAR(100),
            ai_predicted_domain VARCHAR(100),
            reviewer_note TEXT,
            annotation_id INTEGER,
            reviewed_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'pending',
            taxonomy_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
            UNIQUE (posting_id, annotation_id)
        )
        """
    )

    # 이미 존재하지만 taxonomy_version이 없는 경우 추가
    op.execute(
        """
        ALTER TABLE domain_review_staging
        ADD COLUMN IF NOT EXISTS taxonomy_version VARCHAR(20)
        NOT NULL DEFAULT '1.0.0'
        """
    )

    # core_tech_review_staging 테이블 생성
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS core_tech_review_staging (
            id SERIAL PRIMARY KEY,
            posting_id VARCHAR(100) NOT NULL,
            reviewed_technologies JSONB,
            ai_predicted_technologies JSONB,
            reviewer_note TEXT,
            annotation_id INTEGER,
            reviewed_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'pending',
            taxonomy_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
            UNIQUE (posting_id, annotation_id)
        )
        """
    )

    # job_posting 테이블에 taxonomy_version 추가
    op.add_column(
        "job_posting",
        sa.Column(
            "taxonomy_version",
            sa.String(20),
            nullable=True,
        ),
    )

    op.create_index(
        "idx_job_posting_taxonomy_version",
        "job_posting",
        ["taxonomy_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_job_posting_taxonomy_version",
        table_name="job_posting",
    )
    op.drop_column("job_posting", "taxonomy_version")

    op.execute("DROP TABLE IF EXISTS core_tech_review_staging")
    op.execute("DROP TABLE IF EXISTS domain_review_staging")
