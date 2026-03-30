#!/usr/bin/env python3
"""
job_posting 테이블에 domain, core_technologies 컬럼을 추가하는 마이그레이션 스크립트
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.database import db_manager, init_database
from backend.core.logging import create_development_logger
from sqlalchemy import text

logger = create_development_logger(__name__)

def add_domain_core_technologies_columns():
    """job_posting 테이블에 domain, core_technologies 컬럼 추가"""

    print("🏷️ domain, core_technologies 컬럼 추가 시작...")

    # 데이터베이스 초기화
    init_database()

    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False

    try:
        with db_manager.get_session() as session:
            # domain 컬럼 확인 및 추가
            result = session.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'job_posting' AND column_name = 'domain'")
            ).fetchone()

            if result:
                print("ℹ️ domain 컬럼이 이미 존재합니다.")
            else:
                session.execute(
                    text("ALTER TABLE job_posting ADD COLUMN domain VARCHAR(100);")
                )
                print("✅ domain 컬럼이 추가되었습니다.")

            # core_technologies 컬럼 확인 및 추가
            result = session.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'job_posting' AND column_name = 'core_technologies'")
            ).fetchone()

            if result:
                print("ℹ️ core_technologies 컬럼이 이미 존재합니다.")
            else:
                session.execute(
                    text("ALTER TABLE job_posting ADD COLUMN core_technologies JSONB;")
                )
                print("✅ core_technologies 컬럼이 추가되었습니다.")

            # domain 인덱스 생성
            idx_exists = session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'job_posting' AND indexname = 'idx_job_posting_domain'")
            ).fetchone()

            if not idx_exists:
                session.execute(
                    text("CREATE INDEX idx_job_posting_domain ON job_posting (domain);")
                )
                print("✅ idx_job_posting_domain 인덱스가 생성되었습니다.")
            else:
                print("ℹ️ idx_job_posting_domain 인덱스가 이미 존재합니다.")

            session.commit()
            return True

    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        print(f"❌ 마이그레이션 실패: {e}")
        return False

if __name__ == "__main__":
    success = add_domain_core_technologies_columns()

    if success:
        print("\n🎉 데이터베이스 마이그레이션 완료!")
        print("💡 이제 채용공고에 도메인과 핵심 기술 태그를 저장할 수 있습니다.")
    else:
        print("\n❌ 데이터베이스 마이그레이션 실패!")
        sys.exit(1)
