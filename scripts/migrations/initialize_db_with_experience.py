#!/usr/bin/env python3
"""
ExperienceCategory 테이블을 포함한 데이터베이스 초기화 스크립트
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

def initialize_database_with_experience():
    """ExperienceCategory 테이블을 포함하여 데이터베이스 초기화"""
    
    print("🚀 데이터베이스 초기화 시작...")
    print("⚠️  이 작업은 ExperienceCategory 테이블을 새로 생성합니다.")
    
    try:
        # 데이터베이스 초기화
        init_database()
        
        # 연결 테스트
        if db_manager.test_connection():
            print("✅ 데이터베이스 초기화 및 테이블 생성 성공!")
            
            # 테이블 존재 확인
            with db_manager.get_session() as session:
                # ExperienceCategory 테이블 존재 확인
                result = session.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_name = 'experience_categories'")
                ).fetchone()
                
                if result:
                    print("✅ experience_categories 테이블이 성공적으로 생성되었습니다.")
                else:
                    print("❌ experience_categories 테이블 생성에 실패했습니다.")
                    return False
                
                # job_posting 테이블에 experience_category_id 컬럼 확인
                result = session.execute(
                    text("SELECT column_name FROM information_schema.columns WHERE table_name = 'job_posting' AND column_name = 'experience_category_id'")
                ).fetchone()
                
                if result:
                    print("✅ job_posting.experience_category_id 컬럼이 성공적으로 추가되었습니다.")
                else:
                    print("❌ job_posting.experience_category_id 컬럼이 존재하지 않습니다.")
                    return False
            
            return True
        else:
            print("❌ 데이터베이스 연결 테스트 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        return False

if __name__ == "__main__":
    success = initialize_database_with_experience()
    
    if success:
        print("\n🎉 데이터베이스 초기화 완료!")
        print("💡 이제 경력 정규화 기능을 사용할 수 있습니다.")
    else:
        print("\n❌ 데이터베이스 초기화 실패!")
        sys.exit(1)