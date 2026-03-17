#!/usr/bin/env python3
"""
기존 posting_id 패턴을 분석해서 URL 재구성 가능성 확인
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.database import db_manager, init_database
from backend.models import JobPosting
from backend.core.logging import create_development_logger

logger = create_development_logger(__name__)

def analyze_posting_ids():
    """posting_id 패턴을 분석"""
    
    print("🔍 posting_id 패턴 분석 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            # 샘플 posting_id 조회
            job_postings = session.query(JobPosting.posting_id).limit(20).all()
            
            print(f"📊 샘플 posting_id 패턴:")
            for posting in job_postings:
                posting_id = posting[0]
                print(f"  - {posting_id}")
            
            # 패턴별 분류
            wanted_count = session.query(JobPosting).filter(
                JobPosting.posting_id.like('wanted_%')
            ).count()
            
            saramin_count = session.query(JobPosting).filter(
                JobPosting.posting_id.like('saramin_%')
            ).count()
            
            jobkorea_count = session.query(JobPosting).filter(
                JobPosting.posting_id.like('jobkorea_%')
            ).count()
            
            print(f"\n📈 posting_id 패턴 통계:")
            print(f"  - wanted_*: {wanted_count}개")
            print(f"  - saramin_*: {saramin_count}개") 
            print(f"  - jobkorea_*: {jobkorea_count}개")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 분석 실패: {e}")
        print(f"❌ 분석 실패: {e}")
        return False

if __name__ == "__main__":
    analyze_posting_ids()