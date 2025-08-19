"""
Experience normalization utilities for standardizing experience requirements.
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ExperienceNormalizationResult:
    """경력 정규화 결과를 담는 데이터 클래스"""
    raw_experience: str
    clean_experience: str
    standardized_experience: str
    min_years: Optional[int]
    max_years: Optional[int]
    is_fresh_welcome: bool
    confidence: float
    matching_method: str
    manual_review: bool = False
    correction: Optional[str] = None
    review_note: Optional[str] = None

class ExperienceNormalizer:
    """경력 요구사항 정규화를 위한 클래스"""
    
    # 표준 경력 분류
    STANDARD_EXPERIENCE_CATEGORIES = {
        '신입': {'min_years': 0, 'max_years': 0, 'fresh_welcome': True},
        '신입~1년': {'min_years': 0, 'max_years': 1, 'fresh_welcome': True},
        '1~3년': {'min_years': 1, 'max_years': 3, 'fresh_welcome': False},
        '3~5년': {'min_years': 3, 'max_years': 5, 'fresh_welcome': False},
        '5~7년': {'min_years': 5, 'max_years': 7, 'fresh_welcome': False},
        '7~10년': {'min_years': 7, 'max_years': 10, 'fresh_welcome': False},
        '10년 이상': {'min_years': 10, 'max_years': None, 'fresh_welcome': False},
        '경력무관': {'min_years': 0, 'max_years': None, 'fresh_welcome': True}
    }
    
    def __init__(self):
        """ExperienceNormalizer 초기화"""
        self.confidence_threshold = 0.8
        
    def normalize_experience(self, experience: str) -> ExperienceNormalizationResult:
        """
        경력 요구사항을 정규화하는 메인 메서드
        
        Args:
            experience (str): 원본 경력 요구사항
            
        Returns:
            ExperienceNormalizationResult: 정규화 결과
        """
        # 1단계: 텍스트 전처리
        clean_experience = self._clean_experience_text(experience)
        
        # 2단계: 년수 추출
        min_years, max_years = self._extract_years(clean_experience)
        
        # 3단계: 신입 환영 여부 판단
        is_fresh_welcome = self._is_fresh_welcome(clean_experience)
        
        # 4단계: 표준 카테고리 매칭
        standardized, confidence, method = self._categorize_experience(
            min_years, max_years, is_fresh_welcome, clean_experience
        )
        
        return ExperienceNormalizationResult(
            raw_experience=experience,
            clean_experience=clean_experience,
            standardized_experience=standardized,
            min_years=min_years,
            max_years=max_years,
            is_fresh_welcome=is_fresh_welcome,
            confidence=confidence,
            matching_method=method,
            manual_review=confidence < self.confidence_threshold
        )
    
    def _clean_experience_text(self, text: str) -> str:
        """
        경력 텍스트 전처리
        
        Args:
            text (str): 원본 텍스트
            
        Returns:
            str: 정리된 텍스트
        """
        if not text:
            return ""
            
        result = text.strip()
        
        # 불필요한 문자 제거
        result = re.sub(r'[()【】『』「」\[\]]', '', result)
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def _extract_years(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        텍스트에서 년수 정보 추출
        
        Args:
            text (str): 경력 텍스트
            
        Returns:
            Tuple[Optional[int], Optional[int]]: (최소 년수, 최대 년수)
        """
        text = text.lower()
        
        # 패턴 1: "경력 X-Y년" 또는 "경력 X~Y년"
        range_pattern = r'경력\s*(\d+)[-~]\s*(\d+)년'
        match = re.search(range_pattern, text)
        if match:
            min_years = int(match.group(1))
            max_years = int(match.group(2))
            return min_years, max_years
        
        # 패턴 2: "경력 X년 이상"
        min_pattern = r'경력\s*(\d+)년?\s*이상'
        match = re.search(min_pattern, text)
        if match:
            min_years = int(match.group(1))
            return min_years, None
        
        # 패턴 3: "신입-경력 X년"
        fresh_to_exp_pattern = r'신입[-~]\s*경력\s*(\d+)년'
        match = re.search(fresh_to_exp_pattern, text)
        if match:
            max_years = int(match.group(1))
            return 0, max_years
        
        # 패턴 4: "X년 이상"
        years_above_pattern = r'(\d+)년\s*이상'
        match = re.search(years_above_pattern, text)
        if match:
            min_years = int(match.group(1))
            return min_years, None
        
        # 패턴 5: "X-Y년" 또는 "X~Y년"
        simple_range_pattern = r'(\d+)[-~]\s*(\d+)년'
        match = re.search(simple_range_pattern, text)
        if match:
            min_years = int(match.group(1))
            max_years = int(match.group(2))
            return min_years, max_years
        
        # 패턴 6: "경력 X년"
        exact_pattern = r'경력\s*(\d+)년'
        match = re.search(exact_pattern, text)
        if match:
            years = int(match.group(1))
            return years, years
        
        # 패턴 7: 단순히 "X년"
        simple_pattern = r'^(\d+)년$'
        match = re.search(simple_pattern, text.strip())
        if match:
            years = int(match.group(1))
            return years, years
        
        return None, None
    
    def _is_fresh_welcome(self, text: str) -> bool:
        """
        신입 환영 여부 판단
        
        Args:
            text (str): 경력 텍스트
            
        Returns:
            bool: 신입 환영 여부
        """
        text = text.lower()
        
        fresh_keywords = [
            '신입', 'fresh', '경력무관', '경력 무관', 
            '신입 이상', '신입-', '신입~', 'junior'
        ]
        
        return any(keyword in text for keyword in fresh_keywords)
    
    def _categorize_experience(
        self, 
        min_years: Optional[int], 
        max_years: Optional[int], 
        is_fresh_welcome: bool,
        text: str
    ) -> Tuple[str, float, str]:
        """
        경력을 표준 카테고리로 분류
        
        Args:
            min_years: 최소 경력 년수
            max_years: 최대 경력 년수
            is_fresh_welcome: 신입 환영 여부
            text: 원본 텍스트
            
        Returns:
            Tuple[str, float, str]: (표준 카테고리, 신뢰도, 매칭 방법)
        """
        # 직접 매칭 시도
        direct_match = self._direct_text_match(text)
        if direct_match:
            return direct_match, 1.0, "direct_match"
        
        # 년수 기반 분류
        if min_years is not None or max_years is not None:
            category = self._classify_by_years(min_years, max_years, is_fresh_welcome)
            if category:
                return category, 0.9, "years_based"
        
        # 키워드 기반 분류
        keyword_match = self._keyword_based_classification(text)
        if keyword_match:
            return keyword_match, 0.7, "keyword_based"
        
        # 매칭 실패
        return text, 0.0, "no_match"
    
    def _direct_text_match(self, text: str) -> Optional[str]:
        """직접 텍스트 매칭"""
        text_lower = text.lower().strip()
        
        direct_mappings = {
            '신입': '신입',
            '경력무관': '경력무관',
            '경력 무관': '경력무관',
            '신입 이상': '신입~1년',
        }
        
        return direct_mappings.get(text_lower)
    
    def _classify_by_years(
        self, 
        min_years: Optional[int], 
        max_years: Optional[int], 
        is_fresh_welcome: bool
    ) -> Optional[str]:
        """년수 기반 분류"""
        
        # 신입만 가능
        if min_years == 0 and max_years == 0:
            return '신입'
        
        # 신입부터 1년까지
        if min_years == 0 and max_years == 1:
            return '신입~1년'
        
        # 경력무관 (신입 환영 + 상한 없음)
        if is_fresh_welcome and max_years is None:
            return '경력무관'
        
        # 년수 범위 기반 분류
        if min_years is not None and max_years is not None:
            # 1-3년
            if min_years <= 1 and max_years <= 3:
                return '1~3년'
            # 3-5년
            elif min_years <= 3 and max_years <= 5:
                return '3~5년'
            # 5-7년
            elif min_years <= 5 and max_years <= 7:
                return '5~7년'
            # 7-10년
            elif min_years <= 7 and max_years <= 10:
                return '7~10년'
            # 10년 이상
            elif min_years >= 10 or max_years >= 10:
                return '10년 이상'
        
        # 최소 년수만 있는 경우
        if min_years is not None and max_years is None:
            if min_years >= 10:
                return '10년 이상'
            elif min_years >= 7:
                return '7~10년'
            elif min_years >= 5:
                return '5~7년'
            elif min_years >= 3:
                return '3~5년'
            elif min_years >= 1:
                return '1~3년'
            elif min_years == 0:
                return '신입~1년'
        
        return None
    
    def _keyword_based_classification(self, text: str) -> Optional[str]:
        """키워드 기반 분류"""
        text_lower = text.lower()
        
        # 시니어 키워드
        if any(keyword in text_lower for keyword in ['시니어', 'senior', '고급', '책임']):
            return '7~10년'
        
        # 주니어 키워드
        if any(keyword in text_lower for keyword in ['주니어', 'junior', '초급']):
            return '1~3년'
        
        return None
    
    def get_standard_categories(self) -> List[str]:
        """표준 경력 카테고리 목록 반환"""
        return list(self.STANDARD_EXPERIENCE_CATEGORIES.keys())
    
    def get_standardized_value(self, experience: str) -> Optional[str]:
        """
        경력 요구사항에 대한 표준화된 값만 반환 (DB 저장용)
        
        Args:
            experience (str): 원본 경력 요구사항
            
        Returns:
            Optional[str]: 표준화된 경력 (신뢰도가 높은 경우만)
        """
        result = self.normalize_experience(experience)
        
        # 신뢰도가 임계값 이상인 경우만 표준화된 값 반환
        if result.confidence >= self.confidence_threshold:
            return result.standardized_experience
        
        # 신뢰도가 낮은 경우 None 반환 (수동 검토 필요)
        return None
    
    def batch_normalize(self, experiences: List[str]) -> List[ExperienceNormalizationResult]:
        """
        여러 경력 요구사항을 일괄 정규화
        
        Args:
            experiences (List[str]): 경력 요구사항 리스트
            
        Returns:
            List[ExperienceNormalizationResult]: 정규화 결과 리스트
        """
        return [self.normalize_experience(exp) for exp in experiences]