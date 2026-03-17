#!/usr/bin/env python3
"""
deadline 컬럼 데이터 분석 스크립트
"""

import sys
from pathlib import Path
import re

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.database import db_manager, init_database
from backend.models import JobPosting
from backend.core.logging import create_development_logger
from sqlalchemy import text

logger = create_development_logger(__name__)

def analyze_deadline_data():
    """deadline 컬럼의 데이터 패턴 분석"""
    
    print("🔍 deadline 컬럼 데이터 분석 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            # 전체 deadline 데이터 조회
            deadlines = session.query(JobPosting.deadline).filter(
                JobPosting.deadline.isnot(None)
            ).all()
            
            total_count = len(deadlines)
            print(f"📊 전체 deadline 데이터 수: {total_count}")
            
            if total_count == 0:
                print("ℹ️ deadline 데이터가 없습니다.")
                return True
            
            # 패턴별 분석
            always_recruiting_count = 0
            date_pattern_count = 0
            other_patterns = {}
            
            # 날짜 패턴 (예: 2024-12-31, 12/31까지, 2024년 12월 31일)
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # 2024-12-31
                r'\d{2}/\d{2}',        # 12/31
                r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',  # 2024년 12월 31일
                r'\d{1,2}월\s*\d{1,2}일',  # 12월 31일
                r'\d{2}\.\d{2}\.\d{2}',  # 24.12.31
                r'\d{4}\.\d{2}\.\d{2}',  # 2024.12.31
            ]
            
            sample_deadlines = []
            
            for deadline in deadlines[:50]:  # 샘플 50개만 확인
                deadline_text = deadline[0].strip() if deadline[0] else ""
                
                if not deadline_text:
                    continue
                
                sample_deadlines.append(deadline_text)
                
                # 상시채용 패턴 확인
                if any(keyword in deadline_text for keyword in ['상시채용', '상시모집', '상시']):
                    always_recruiting_count += 1
                else:
                    # 날짜 패턴 확인
                    is_date_pattern = False
                    for pattern in date_patterns:
                        if re.search(pattern, deadline_text):
                            date_pattern_count += 1
                            is_date_pattern = True
                            break
                    
                    if not is_date_pattern:
                        # 기타 패턴
                        pattern_key = deadline_text[:20]  # 처음 20자만
                        other_patterns[pattern_key] = other_patterns.get(pattern_key, 0) + 1
            
            print(f"\n📈 패턴 분석 결과 (샘플 {len(sample_deadlines)}개):")
            print(f"  📅 날짜 패턴: {date_pattern_count}")
            print(f"  🔄 상시채용: {always_recruiting_count}")
            print(f"  ❓ 기타 패턴: {len(other_patterns)}")
            
            print(f"\n📋 샘플 deadline 값들:")
            for i, deadline in enumerate(sample_deadlines[:20], 1):
                print(f"  {i:2d}. '{deadline}'")
                
            if other_patterns:
                print(f"\n❓ 기타 패턴들:")
                for pattern, count in list(other_patterns.items())[:10]:
                    print(f"  - '{pattern}' (등장 횟수: {count})")
            
            # 전체 통계 (전체 데이터로 상시채용 개수 확인)
            always_recruiting_total = session.execute(
                text("SELECT COUNT(*) FROM job_posting WHERE deadline LIKE '%상시%' OR deadline LIKE '%상시채용%' OR deadline LIKE '%상시모집%'")
            ).scalar()
            
            print(f"\n🎯 전체 통계:")
            print(f"  📊 전체 레코드: {total_count}")
            print(f"  🔄 상시채용 (추정): {always_recruiting_total}")
            print(f"  📅 날짜 기반 (추정): {total_count - always_recruiting_total}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 데이터 분석 실패: {e}")
        print(f"❌ 데이터 분석 실패: {e}")
        return False

if __name__ == "__main__":
    success = analyze_deadline_data()
    
    if success:
        print("\n✅ deadline 데이터 분석 완료!")
    else:
        print("\n❌ 데이터 분석 실패!")
        sys.exit(1)