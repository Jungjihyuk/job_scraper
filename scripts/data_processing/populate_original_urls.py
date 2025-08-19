#!/usr/bin/env python3
"""
기존 job_posting 레코드에 original_url을 업데이트하는 스크립트
URL에서 posting_id를 추출하여 연결
"""

import sys
import re
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from job_scraper.database.connection import db_manager, init_database
from job_scraper.database.models import JobPosting, ScrapedUrl
from job_scraper.config.logging_config import create_development_logger

logger = create_development_logger(__name__)

def extract_posting_id_from_url(url: str) -> str:
    """URL에서 posting_id를 추출"""
    # 원티드: /wd/123456
    wanted_match = re.search(r'/wd/(\d+)', url)
    if wanted_match:
        return f"wanted_{wanted_match.group(1)}"
    
    # 사람인: /ZR_C/123456 또는 /job/123456
    saramin_match = re.search(r'/(?:ZR_C|job)/(\d+)', url)
    if saramin_match:
        return f"saramin_{saramin_match.group(1)}"
    
    # 잡코리아: /Recruit/123456
    jobkorea_match = re.search(r'/Recruit/(\d+)', url)
    if jobkorea_match:
        return f"jobkorea_{jobkorea_match.group(1)}"
    
    return None

def populate_original_urls():
    """기존 job_posting 레코드에 original_url 정보 추가"""
    
    print("🔗 original_url 정보 업데이트 시작...")
    
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
            
            # 모든 ScrapedUrl 조회
            scraped_urls = session.query(ScrapedUrl).filter(
                ScrapedUrl.status == 'completed'
            ).all()
            
            print(f"🌐 스크래핑된 URL 수: {len(scraped_urls)}")
            
            # URL에서 posting_id 추출하여 매핑
            url_mapping = {}
            for scraped_url in scraped_urls:
                extracted_id = extract_posting_id_from_url(scraped_url.url)
                if extracted_id:
                    url_mapping[extracted_id] = scraped_url.url
            
            print(f"🔍 추출된 posting_id 개수: {len(url_mapping)}")
            
            # job_posting과 URL 매칭 및 업데이트
            matched_count = 0
            for job in null_url_jobs:
                if job.posting_id in url_mapping:
                    job.original_url = url_mapping[job.posting_id]
                    matched_count += 1
            
            # 변경 사항 저장
            session.commit()
            
            print(f"✅ original_url 업데이트 완료:")
            print(f"  - 전체 대상: {len(null_url_jobs)}건")
            print(f"  - 매칭 성공: {matched_count}건")
            print(f"  - 매칭 실패: {len(null_url_jobs) - matched_count}건")
            
            if matched_count > 0:
                print(f"📋 매칭 성공 예시:")
                updated_jobs = session.query(JobPosting).filter(
                    JobPosting.original_url.isnot(None)
                ).limit(3).all()
                
                for job in updated_jobs:
                    print(f"  - {job.posting_id}: {job.position} → {job.original_url[:80]}...")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ URL 업데이트 실패: {e}")
        print(f"❌ URL 업데이트 실패: {e}")
        return False

if __name__ == "__main__":
    success = populate_original_urls()
    
    if success:
        print("\n🎉 original_url 업데이트 완료!")
        print("💡 이제 채용공고 제목을 클릭하면 원본 사이트로 이동할 수 있습니다.")
    else:
        print("\n❌ original_url 업데이트 실패!")
        sys.exit(1)