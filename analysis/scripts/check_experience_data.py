#!/usr/bin/env python3
"""
ExperienceCategory 데이터 확인 스크립트
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.database import db_manager, init_database
from backend.models import ExperienceCategory, JobPosting
from backend.core.logging import create_development_logger

logger = create_development_logger(__name__)

def check_experience_data():
    """ExperienceCategory 테이블 데이터 확인"""
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            # ExperienceCategory 테이블 데이터 확인
            experience_count = session.query(ExperienceCategory).count()
            print(f"📊 ExperienceCategory 레코드 수: {experience_count}")
            
            if experience_count > 0:
                print("\n📋 상위 10개 경력 카테고리:")
                categories = session.query(ExperienceCategory).limit(10).all()
                for cat in categories:
                    print(f"  - {cat.raw_experience} → {cat.standardized_experience} (신뢰도: {cat.confidence})")
            else:
                print("ℹ️ ExperienceCategory 테이블이 비어있습니다.")
            
            # job_posting 테이블에서 experience_category_id가 설정된 레코드 확인
            linked_jobs = session.query(JobPosting).filter(JobPosting.experience_category_id.isnot(None)).count()
            print(f"\n🔗 경력 카테고리가 연결된 채용공고 수: {linked_jobs}")
            
            # 전체 채용공고 수
            total_jobs = session.query(JobPosting).count()
            print(f"📊 전체 채용공고 수: {total_jobs}")
            
            if total_jobs > 0 and linked_jobs == 0:
                print("⚠️ 경력 정규화 데이터를 생성해야 합니다.")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"❌ 데이터 확인 실패: {e}")
        print(f"❌ 데이터 확인 실패: {e}")
        return False

if __name__ == "__main__":
    success = check_experience_data()
    
    if success:
        print("\n✅ 경력 정규화 데이터가 정상적으로 설정되어 있습니다!")
    else:
        print("\n⚠️ 경력 정규화 데이터를 생성하거나 업데이트해야 합니다.")