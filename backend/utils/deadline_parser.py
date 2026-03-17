"""
마감일 파싱 유틸리티
"""

import re
from datetime import datetime, date
from typing import Tuple, Optional
from backend.core.logging import create_development_logger

logger = create_development_logger(__name__)

class DeadlineParser:
    """마감일 텍스트를 파싱하여 구조화된 데이터로 변환"""
    
    def __init__(self):
        self.always_recruiting_keywords = ['상시', '상시채용', '상시모집', '수시', '수시채용']
        
    def parse_deadline(self, deadline_text: str) -> Tuple[Optional[date], bool]:
        """
        마감일 텍스트를 파싱하여 날짜와 상시채용 여부 반환
        
        Args:
            deadline_text (str): 원본 마감일 텍스트
            
        Returns:
            Tuple[Optional[date], bool]: (파싱된 날짜, 상시채용 여부)
        """
        if not deadline_text or deadline_text.strip() == "":
            return None, False
        
        deadline_text = deadline_text.strip()
        
        # 상시채용 여부 확인
        is_always_recruiting = any(
            keyword in deadline_text 
            for keyword in self.always_recruiting_keywords
        )
        
        if is_always_recruiting:
            return None, True
        
        # 날짜 파싱 시도
        parsed_date = self._parse_date(deadline_text)
        return parsed_date, False
    
    def _parse_date(self, deadline_text: str) -> Optional[date]:
        """다양한 날짜 형식을 파싱하여 date 객체 반환"""
        try:
            # 패턴 1: 2025.07.30, 2024.12.31
            match = re.match(r'(\d{4})\.(\d{2})\.(\d{2})', deadline_text)
            if match:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
            
            # 패턴 2: 2025-07-30, 2024-12-31
            match = re.match(r'(\d{4})-(\d{2})-(\d{2})', deadline_text)
            if match:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
            
            # 패턴 3: 07/30, 12/31 (현재 연도 가정)
            match = re.match(r'(\d{1,2})/(\d{1,2})', deadline_text)
            if match:
                month, day = map(int, match.groups())
                current_year = datetime.now().year
                return date(current_year, month, day)
            
            # 패턴 4: 2024년 12월 31일
            match = re.match(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', deadline_text)
            if match:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
            
            # 패턴 5: 12월 31일 (현재 연도 가정)
            match = re.match(r'(\d{1,2})월\s*(\d{1,2})일', deadline_text)
            if match:
                month, day = map(int, match.groups())
                current_year = datetime.now().year
                return date(current_year, month, day)
            
            # 패턴 6: 07.30, 12.31 (현재 연도 가정)
            match = re.match(r'(\d{1,2})\.(\d{1,2})$', deadline_text)
            if match:
                month, day = map(int, match.groups())
                current_year = datetime.now().year
                return date(current_year, month, day)
                
            logger.debug(f"인식할 수 없는 날짜 형식: '{deadline_text}'")
            return None
            
        except (ValueError, TypeError) as e:
            logger.warning(f"날짜 파싱 오류: '{deadline_text}' - {e}")
            return None