#!/usr/bin/env python3
"""
Experience category ID 컬럼을 job_posting 테이블에 추가하는 마이그레이션 스크립트
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

def add_experience_category_id_column():
    """job_posting 테이블에 experience_category_id 컬럼 추가"""
    
    print("🔧 experience_category_id 컬럼 추가 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            # 컬럼이 이미 존재하는지 확인
            result = session.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'job_posting' AND column_name = 'experience_category_id'")
            ).fetchone()
            
            if result:
                print("ℹ️ experience_category_id 컬럼이 이미 존재합니다.")
                return True
            
            # 컬럼 추가
            session.execute(
                text("ALTER TABLE job_posting ADD COLUMN experience_category_id INTEGER REFERENCES experience_categories(experience_category_id);")
            )
            session.commit()
            
            print("✅ experience_category_id 컬럼이 성공적으로 추가되었습니다.")
            
            # 인덱스 추가
            session.execute(
                text("CREATE INDEX IF NOT EXISTS idx_job_posting_experience ON job_posting(experience_category_id);")
            )
            session.commit()
            
            print("✅ experience_category_id 인덱스가 성공적으로 추가되었습니다.")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 컬럼 추가 실패: {e}")
        print(f"❌ 컬럼 추가 실패: {e}")
        return False

if __name__ == "__main__":
    success = add_experience_category_id_column()
    
    if success:
        print("\n🎉 데이터베이스 마이그레이션 완료!")
        print("💡 이제 경력 정규화 기능을 사용할 수 있습니다.")
    else:
        print("\n❌ 데이터베이스 마이그레이션 실패!")
        sys.exit(1)