#!/usr/bin/env python3
"""
기존 posting_id를 사용해서 URL을 재구성하는 스크립트
일반적인 채용사이트 패턴으로 URL 생성
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import db_manager, init_database
from app.models import JobPosting
from app.core.logging import create_development_logger

logger = create_development_logger(__name__)

def reconstruct_urls():
    """posting_id를 기반으로 URL 재구성"""
    
    print("🔧 URL 재구성 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            # original_url이 null인 job_posting 조회
            null_url_jobs = session.query(JobPosting).filter(
                JobPosting.original_url.is_(None)
            ).all()
            
            print(f"📊 URL이 없는 채용공고 수: {len(null_url_jobs)}")
            
            if len(null_url_jobs) == 0:
                print("ℹ️ 모든 채용공고에 URL이 설정되어 있습니다.")
                return True
            
            # URL 재구성 및 업데이트
            updated_count = 0
            
            for job in null_url_jobs:
                # 숫자 ID로 보아서 원티드일 가능성이 높음
                # 원티드 URL 패턴: https://www.wanted.co.kr/wd/{posting_id}
                if job.posting_id.isdigit():
                    job.original_url = f"https://www.wanted.co.kr/wd/{job.posting_id}"
                    updated_count += 1
            
            # 변경 사항 저장
            session.commit()
            
            print(f"✅ URL 재구성 완료:")
            print(f"  - 전체 대상: {len(null_url_jobs)}건")
            print(f"  - 업데이트: {updated_count}건")
            
            if updated_count > 0:
                print(f"📋 재구성된 URL 예시:")
                updated_jobs = session.query(JobPosting).filter(
                    JobPosting.original_url.isnot(None)
                ).limit(3).all()
                
                for job in updated_jobs:
                    print(f"  - {job.posting_id}: {job.position}")
                    print(f"    → {job.original_url}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ URL 재구성 실패: {e}")
        print(f"❌ URL 재구성 실패: {e}")
        return False

if __name__ == "__main__":
    success = reconstruct_urls()
    
    if success:
        print("\n🎉 URL 재구성 완료!")
        print("💡 이제 채용공고 제목을 클릭하면 원본 사이트로 이동할 수 있습니다.")
        print("⚠️  일부 URL이 유효하지 않을 수 있습니다.")
    else:
        print("\n❌ URL 재구성 실패!")
        sys.exit(1)