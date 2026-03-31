"""add company classification columns (FR-054)

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("company_type", sa.String(50)))
    op.add_column("companies", sa.Column("company_type_labels", JSONB))
    op.add_column("companies", sa.Column("ai_confidence", sa.Float))
    op.add_column("companies", sa.Column("source_info", JSONB))

    op.create_index("idx_companies_type", "companies", ["company_type"])
    op.create_unique_constraint("uq_companies_name", "companies", ["company_name"])


def downgrade() -> None:
    op.drop_constraint("uq_companies_name", "companies", type_="unique")
    op.drop_index("idx_companies_type", table_name="companies")

    op.drop_column("companies", "source_info")
    op.drop_column("companies", "ai_confidence")
    op.drop_column("companies", "company_type_labels")
    op.drop_column("companies", "company_type")
