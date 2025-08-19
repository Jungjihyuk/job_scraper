#!/usr/bin/env python3
"""
job_posting 테이블에 original_url 컬럼을 추가하는 마이그레이션 스크립트
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from job_scraper.database.connection import db_manager, init_database
from job_scraper.config.logging_config import create_development_logger
from sqlalchemy import text

logger = create_development_logger(__name__)

def add_original_url_column():
    """job_posting 테이블에 original_url 컬럼 추가"""
    
    print("🔗 original_url 컬럼 추가 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            # 컬럼이 이미 존재하는지 확인
            result = session.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'job_posting' AND column_name = 'original_url'")
            ).fetchone()
            
            if result:
                print("ℹ️ original_url 컬럼이 이미 존재합니다.")
                return True
            
            # 컬럼 추가
            session.execute(
                text("ALTER TABLE job_posting ADD COLUMN original_url VARCHAR(2048);")
            )
            session.commit()
            
            print("✅ original_url 컬럼이 성공적으로 추가되었습니다.")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 컬럼 추가 실패: {e}")
        print(f"❌ 컬럼 추가 실패: {e}")
        return False

if __name__ == "__main__":
    success = add_original_url_column()
    
    if success:
        print("\n🎉 데이터베이스 마이그레이션 완료!")
        print("💡 이제 채용공고 제목에 원본 URL 링크를 추가할 수 있습니다.")
    else:
        print("\n❌ 데이터베이스 마이그레이션 실패!")
        sys.exit(1)