#!/usr/bin/env python3
"""
deadline 컬럼 구조를 개선하는 마이그레이션 스크립트
- is_always_recruiting 컬럼 추가
- deadline 컬럼을 DATE 타입으로 변경
- 기존 데이터를 적절히 변환
"""

import sys
from pathlib import Path
import re
from datetime import datetime

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from job_scraper.database.connection import db_manager, init_database
from job_scraper.config.logging_config import create_development_logger
from sqlalchemy import text

logger = create_development_logger(__name__)

def migrate_deadline_structure():
    """deadline 테이블 구조 마이그레이션"""
    
    print("🚀 deadline 구조 마이그레이션 시작...")
    
    # 데이터베이스 초기화
    init_database()
    
    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False
    
    try:
        with db_manager.get_session() as session:
            
            print("📋 1단계: 백업용 임시 컬럼 생성...")
            # 백업용 컬럼 추가
            session.execute(
                text("ALTER TABLE job_posting ADD COLUMN IF NOT EXISTS deadline_backup VARCHAR(50);")
            )
            session.commit()
            
            # 기존 deadline 데이터 백업
            session.execute(
                text("UPDATE job_posting SET deadline_backup = deadline WHERE deadline_backup IS NULL;")
            )
            session.commit()
            print("✅ 기존 데이터 백업 완료")
            
            print("📋 2단계: 새로운 컬럼들 추가...")
            # is_always_recruiting 컬럼 추가
            session.execute(
                text("ALTER TABLE job_posting ADD COLUMN IF NOT EXISTS is_always_recruiting BOOLEAN DEFAULT FALSE;")
            )
            session.commit()
            print("✅ is_always_recruiting 컬럼 추가 완료")
            
            print("📋 3단계: 데이터 변환...")
            # 상시채용 플래그 설정
            result = session.execute(
                text("""
                UPDATE job_posting 
                SET is_always_recruiting = TRUE 
                WHERE deadline_backup LIKE '%상시%' 
                   OR deadline_backup LIKE '%상시채용%' 
                   OR deadline_backup LIKE '%상시모집%'
                """)
            )
            always_recruiting_count = result.rowcount
            print(f"✅ 상시채용 플래그 설정: {always_recruiting_count}건")
            
            print("📋 4단계: deadline 컬럼 타입 변경...")
            # deadline 컬럼을 임시로 NULL로 설정
            session.execute(text("UPDATE job_posting SET deadline = NULL;"))
            session.commit()
            
            # deadline 컬럼 타입을 DATE로 변경
            session.execute(
                text("ALTER TABLE job_posting ALTER COLUMN deadline TYPE DATE USING NULL;")
            )
            session.commit()
            print("✅ deadline 컬럼 타입 변경 완료")
            
            print("📋 5단계: 날짜 데이터 파싱 및 변환...")
            # 상시채용이 아닌 레코드들의 날짜 파싱
            date_records = session.execute(
                text("""
                SELECT id, deadline_backup 
                FROM job_posting 
                WHERE is_always_recruiting = FALSE 
                AND deadline_backup IS NOT NULL
                AND deadline_backup != ''
                """)
            ).fetchall()
            
            successful_conversions = 0
            failed_conversions = 0
            
            for record_id, deadline_text in date_records:
                try:
                    parsed_date = parse_deadline_date(deadline_text)
                    if parsed_date:
                        session.execute(
                            text("UPDATE job_posting SET deadline = :date WHERE id = :id"),
                            {"date": parsed_date, "id": record_id}
                        )
                        successful_conversions += 1
                    else:
                        failed_conversions += 1
                        print(f"⚠️ 날짜 파싱 실패: ID {record_id}, 값: '{deadline_text}'")
                        
                except Exception as e:
                    failed_conversions += 1
                    logger.warning(f"날짜 변환 실패: ID {record_id}, 값: '{deadline_text}', 오류: {e}")
            
            session.commit()
            
            print(f"✅ 날짜 변환 완료:")
            print(f"  - 성공: {successful_conversions}건")
            print(f"  - 실패: {failed_conversions}건")
            
            print("📋 6단계: 인덱스 생성...")
            # 인덱스 생성
            session.execute(
                text("CREATE INDEX IF NOT EXISTS idx_job_posting_deadline ON job_posting(deadline);")
            )
            session.execute(
                text("CREATE INDEX IF NOT EXISTS idx_job_posting_always_recruiting ON job_posting(is_always_recruiting);")
            )
            session.commit()
            print("✅ 인덱스 생성 완료")
            
            print("📋 7단계: 최종 통계...")
            # 최종 통계
            stats = session.execute(
                text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_always_recruiting = TRUE THEN 1 ELSE 0 END) as always_recruiting,
                    SUM(CASE WHEN deadline IS NOT NULL THEN 1 ELSE 0 END) as with_deadline
                FROM job_posting
                """)
            ).fetchone()
            
            print(f"📊 마이그레이션 완료 통계:")
            print(f"  - 전체 레코드: {stats.total}")
            print(f"  - 상시채용: {stats.always_recruiting}")
            print(f"  - 마감일 설정: {stats.with_deadline}")
            
            # 백업 컬럼은 유지 (추후 검증 후 삭제 가능)
            print("ℹ️ deadline_backup 컬럼은 검증용으로 유지됩니다.")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        print(f"❌ 마이그레이션 실패: {e}")
        return False

def parse_deadline_date(deadline_text: str):
    """다양한 날짜 형식을 파싱하여 DATE 객체 반환"""
    if not deadline_text or deadline_text.strip() == "":
        return None
    
    deadline_text = deadline_text.strip()
    
    # 상시채용 관련 키워드가 있으면 None 반환
    if any(keyword in deadline_text for keyword in ['상시', '채용', '모집']):
        return None
    
    try:
        # 패턴 1: 2025.07.30, 2024.12.31
        match = re.match(r'(\d{4})\.(\d{2})\.(\d{2})', deadline_text)
        if match:
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day)).date()
        
        # 패턴 2: 2025-07-30, 2024-12-31
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})', deadline_text)
        if match:
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day)).date()
        
        # 패턴 3: 07/30, 12/31 (현재 연도 가정)
        match = re.match(r'(\d{1,2})/(\d{1,2})', deadline_text)
        if match:
            month, day = match.groups()
            current_year = datetime.now().year
            return datetime(current_year, int(month), int(day)).date()
        
        # 패턴 4: 2024년 12월 31일
        match = re.match(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', deadline_text)
        if match:
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day)).date()
        
        # 패턴 5: 12월 31일 (현재 연도 가정)
        match = re.match(r'(\d{1,2})월\s*(\d{1,2})일', deadline_text)
        if match:
            month, day = match.groups()
            current_year = datetime.now().year
            return datetime(current_year, int(month), int(day)).date()
        
        print(f"⚠️ 인식할 수 없는 날짜 형식: '{deadline_text}'")
        return None
        
    except (ValueError, TypeError) as e:
        print(f"❌ 날짜 파싱 오류: '{deadline_text}' - {e}")
        return None

if __name__ == "__main__":
    success = migrate_deadline_structure()
    
    if success:
        print("\n🎉 deadline 구조 마이그레이션 완료!")
        print("💡 이제 날짜 기반 정렬 및 필터링이 효율적으로 가능합니다.")
    else:
        print("\n❌ 마이그레이션 실패!")
        sys.exit(1)