"""
domain_review_staging 테이블 생성 마이그레이션.
Label Studio 검수 결과를 운영 DB에 반영하기 전 staging 영역.

사용법:
    python backend/migrations_legacy/create_domain_staging_table.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import db_manager, init_database
from backend.core.logging import create_development_logger
from sqlalchemy import text

logger = create_development_logger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS domain_review_staging (
    id SERIAL PRIMARY KEY,
    posting_id VARCHAR(100) NOT NULL,
    reviewed_domain VARCHAR(100) NOT NULL,
    ai_predicted_domain VARCHAR(100),
    reviewer_note TEXT,
    annotation_id INTEGER,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    UNIQUE(posting_id, annotation_id)
);

CREATE INDEX IF NOT EXISTS idx_staging_status ON domain_review_staging(status);
CREATE INDEX IF NOT EXISTS idx_staging_posting ON domain_review_staging(posting_id);
"""


def run_migration():
    if not init_database():
        logger.error("Failed to initialize database")
        return False

    try:
        with db_manager.get_session() as session:
            for statement in CREATE_TABLE_SQL.strip().split(";"):
                statement = statement.strip()
                if statement:
                    session.execute(text(statement))
            logger.info("domain_review_staging table created successfully")
            return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
