#!/usr/bin/env python3
"""
기존 데이터베이스의 경력 데이터를 정규화하고 ExperienceCategory와 연결하는 스크립트
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from job_scraper.database.connection import db_manager, init_database
from job_scraper.database.models import JobPosting, ExperienceCategory
from job_scraper.utils.experience_normalizer import ExperienceNormalizer
from job_scraper.config.logging_config import create_development_logger
from sqlalchemy.orm import sessionmaker

logger = create_development_logger(__name__)

def normalize_existing_experience_data():
    """기존 job_posting 테이블의 경력 데이터를 정규화"""
    
    print("🚀 기존 경력 데이터 정규화 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    normalizer = ExperienceNormalizer()
    success_count = 0
    total_count = 0
    skip_count = 0
    
    try:
        with db_manager.get_session() as session:
            # 경력 정보가 있지만 experience_category_id가 없는 job_posting 레코드들을 가져옴
            job_postings = session.query(JobPosting).filter(
                JobPosting.experience.isnot(None),
                JobPosting.experience_category_id.is_(None)
            ).all()
            
            total_count = len(job_postings)
            print(f"📊 정규화할 채용공고 수: {total_count}")
            
            if total_count == 0:
                print("ℹ️ 정규화할 경력 데이터가 없습니다.")
                return True
            
            for job_posting in job_postings:
                try:
                    experience_text = job_posting.experience.strip()
                    if not experience_text:
                        skip_count += 1
                        continue
                    
                    # 이미 ExperienceCategory에 해당 경력이 있는지 확인
                    existing_category = session.query(ExperienceCategory).filter_by(
                        raw_experience=experience_text
                    ).first()
                    
                    if existing_category:
                        # 기존 카테고리와 연결
                        job_posting.experience_category_id = existing_category.experience_category_id
                        success_count += 1
                    else:
                        # 새로운 경력 정규화 및 카테고리 생성
                        result = normalizer.normalize_experience(experience_text)
                        
                        # 새 ExperienceCategory 레코드 생성
                        new_category = ExperienceCategory(
                            raw_experience=result.raw_experience,
                            standardized_experience=result.standardized_experience,
                            min_years=result.min_years,
                            max_years=result.max_years,
                            is_fresh_welcome=result.is_fresh_welcome,
                            confidence=result.confidence,
                            matching_method=result.matching_method,
                            manual_review=result.manual_review
                        )
                        
                        session.add(new_category)
                        session.flush()  # ID 생성을 위한 flush
                        
                        # job_posting과 연결
                        job_posting.experience_category_id = new_category.experience_category_id
                        success_count += 1
                        
                        print(f"✅ 새 카테고리 생성: '{experience_text}' → '{result.standardized_experience}'")
                    
                    # 100개마다 커밋
                    if success_count % 100 == 0:
                        session.commit()
                        print(f"💾 중간 저장: {success_count}/{total_count} 완료")
                        
                except Exception as e:
                    logger.error(f"❌ 항목 처리 실패 (posting_id: {job_posting.posting_id}): {e}")
                    continue
            
            # 최종 커밋
            session.commit()
            
            print(f"\n🎉 경력 정규화 완료!")
            print(f"  📊 전체: {total_count}")
            print(f"  ✅ 성공: {success_count}")
            print(f"  ⏭️  건너뜀: {skip_count}")
            print(f"  ❌ 실패: {total_count - success_count - skip_count}")
            
            # 최종 통계
            linked_jobs = session.query(JobPosting).filter(JobPosting.experience_category_id.isnot(None)).count()
            total_categories = session.query(ExperienceCategory).count()
            
            print(f"\n📈 최종 통계:")
            print(f"  🔗 경력 카테고리가 연결된 채용공고: {linked_jobs}")
            print(f"  📂 전체 경력 카테고리 수: {total_categories}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 경력 데이터 정규화 실패: {e}")
        print(f"❌ 경력 데이터 정규화 실패: {e}")
        return False

if __name__ == "__main__":
    success = normalize_existing_experience_data()
    
    if success:
        print("\n🎊 모든 작업이 성공적으로 완료되었습니다!")
    else:
        print("\n💥 작업 실행 중 오류가 발생했습니다!")
        sys.exit(1)