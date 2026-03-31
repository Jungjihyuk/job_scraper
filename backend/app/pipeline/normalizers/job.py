"""
Job position normalization utilities for standardizing job titles.
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class NormalizationResult:
    """정규화 결과를 담는 데이터 클래스"""
    raw_title: str
    clean_title: str
    standardized_title: str
    confidence: float
    matching_method: str
    manual_review: bool = False
    correction: Optional[str] = None
    review_note: Optional[str] = None

class JobNormalizer:
    """직무명 정규화를 위한 클래스"""
    
    # 표준 직무 분류와 매칭 규칙
    JOB_NORMALIZATION_RULES = {
        '데이터 엔지니어': [
            'data engineer', 'data 엔지니어', '데이터 engineer', '데이터 엔지니어',
            'de', 'data infrastructure engineer', 'ai/deep learning 연구개발자'
        ],
        
        'AI 엔지니어': [
            'ai engineer', 'ai developer', 'ai 개발자', 'ai 엔지니어',
            'ml engineer', 'machine learning engineer', 'ml 엔지니어',
            '머신러닝 engineer', 'machine learning developer', '머신러닝 엔지니어',
            'deep learning engineer', 'dl engineer', '딥러닝 엔지니어',
            'ml/dl engineer', 'llm engineer', 'ai(llm) 엔지니어'
        ],
        
        '데이터 사이언티스트': [
            'data scientist', 'data 사이언티스트', '데이터 scientist',
            'ds', 'data science', 'applied scientist'
        ],
        
        '데이터 분석가': [
            'data analyst', 'data 분석가', '데이터 analyst', '데이터 분석가',
            'business analyst', 'da', 'ba', 'data analytics'
        ],
        
        'AI 연구원': [
            'ai researcher', 'ml researcher', 'ai 연구원',
            'machine learning researcher', 'research scientist',
            'ai research engineer', 'research 연구원'
        ],
        
        '백엔드 개발자': [
            'backend developer', 'backend engineer', '백엔드 developer', '백엔드 개발자',
            'server developer', 'api developer'
        ],
        
        '프론트엔드 개발자': [
            'frontend developer', 'frontend engineer', '프론트엔드 developer',
            'web frontend developer', 'ui developer'
        ],
        
        '풀스택 개발자': [
            'fullstack developer', 'full stack developer', 'full-stack developer',
            'fullstack engineer', '풀스택 developer'
        ]
    }
    
    def __init__(self):
        """JobNormalizer 초기화"""
        self.confidence_threshold = 0.8
        
    def normalize_position(self, position: str) -> NormalizationResult:
        """
        직무명을 정규화하는 메인 메서드
        
        Args:
            position (str): 원본 직무명
            
        Returns:
            NormalizationResult: 정규화 결과
        """
        # 1단계: 텍스트 전처리
        clean_title = self._clean_job_title(position)
        
        # 2단계: 규칙 기반 정규화
        standardized_title, confidence, method = self._normalize_by_rules(clean_title)
        
        return NormalizationResult(
            raw_title=position,
            clean_title=clean_title,
            standardized_title=standardized_title,
            confidence=confidence,
            matching_method=method,
            manual_review=confidence < self.confidence_threshold
        )
    
    def _clean_job_title(self, text: str) -> str:
        """
        직무명 텍스트 전처리
        
        Args:
            text (str): 원본 텍스트
            
        Returns:
            str: 정리된 텍스트
        """
        result = text.strip()
        
        # 1. 소괄호/대괄호 포함 문자 제거 
        result = self._clean_bracket(result)
        
        # 2. 하이픈/대시 뒤 부가설명 제거 (조건부)
        result = self._remove_dash_descriptions(result)
        
        # 3. 슬래시 기반 문자열 정리
        result = self._normalize_slash_terms(result)
        
        # 4. 경력/레벨 표현 제거
        result = self._remove_experience_terms(result)
       
        # 5. 미처리된 괄호/대괄호 잔여물 제거
        result = re.sub(r'[\(\)\[\]]+', '', result)
        
        # 6. 최종 공백 정리
        result = re.sub(r'\s{2,}', ' ', result).strip()
        
        return result
    
    def _clean_bracket(self, text: str) -> str:
        """괄호 내용 제거"""
        all_bracket_pattern = r"[(\[]([^)\]]*)[)\]]"
        result = re.sub(all_bracket_pattern, '', text)
        return result

    def _remove_dash_descriptions(self, text: str) -> str:
        """하이픈 뒤 설명 제거 (신중하게)"""
        # 안전한 제거 패턴들
        safe_remove_patterns = [
            r'\s*-\s*전문연구요원.*',
            r'\s*-\s*\d+년.*경력.*',
            r'\s*-\s*신입.*',
            r'\s*-\s*경력.*',
            r'\s*-\s*근무지.*',
            r'\s*-\s*모델\s+진단.*',  # "모델 진단 및 거버넌스 구축" 같은 부가설명
        ]
        
        for pattern in safe_remove_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text

    def _normalize_slash_terms(self, text: str) -> str:
        """슬래시 기반 용어 정규화"""
        # 중복/유사 기술 용어 정리
        redundant_patterns = {
            r'생성형\s*AI/LLM': 'LLM',
            r'AI/LLM': 'LLM', 
            r'ML/머신러닝': 'ML',
            r'머신러닝/ML': 'ML',
            r'백엔드/ML': 'Backend ML',
            r'프론트엔드·백엔드': 'Fullstack',
            r'Frontend/Backend': 'Fullstack',
        }
        
        for pattern, replacement in redundant_patterns.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text

    def _remove_experience_terms(self, text: str) -> str:
        """경력/레벨 표현 제거"""
        experience_patterns = [
            r'\d+~\d+년차',
            r'\d+-\d+년차', 
            r'신입~초급',
            r'주니어|Junior|Jr\.',
            r'시니어|Senior|Sr\.',
            r'리더|Leader',
            r'리드|Lead',
        ]
        
        for pattern in experience_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text

    def _normalize_by_rules(self, text: str) -> tuple[str, float, str]:
        """
        규칙 기반 정규화
        
        Args:
            text (str): 정리된 직무명
            
        Returns:
            tuple: (표준 직무명, 신뢰도, 매칭 방법)
        """
        lower_text = text.lower()
        
        for standard_name, name_list in self.JOB_NORMALIZATION_RULES.items():
            if lower_text in name_list:
                return standard_name, 1.0, "rule_based"
        
        # 부분 매칭 시도 (신뢰도 낮음)
        for standard_name, name_list in self.JOB_NORMALIZATION_RULES.items():
            for pattern in name_list:
                if pattern in lower_text or lower_text in pattern:
                    return standard_name, 0.6, "partial_match"
        
        # 매칭 실패 시 원본 반환
        return text, 0.0, "no_match"
    
    # 본문 키워드 기반 직무 추론 규칙
    BODY_KEYWORD_RULES: Dict[str, List[str]] = {
        '데이터 엔지니어': [
            'ETL', 'ELT', 'data pipeline', '데이터 파이프라인', 'spark', 'kafka',
            'airflow', 'hadoop', 'data warehouse', '데이터 웨어하우스',
            'data lake', '데이터 레이크', 'dbt', 'hive', 'presto',
        ],
        'AI 엔지니어': [
            'LLM', 'GPT', 'transformer', '모델 학습', 'model training',
            'fine-tuning', '파인튜닝', 'pytorch', 'tensorflow',
            'inference', '추론', 'RAG', 'embedding',
        ],
        '데이터 사이언티스트': [
            '통계 분석', 'statistical analysis', 'A/B 테스트', 'A/B test',
            '가설 검증', 'hypothesis', '예측 모델', 'predictive',
            'feature engineering', '피처 엔지니어링', 'scikit-learn',
        ],
        '데이터 분석가': [
            'SQL', '대시보드', 'dashboard', 'tableau', 'looker',
            '지표', 'KPI', 'metric', '리포트', 'report',
            'GA', 'google analytics', '분석 결과',
        ],
        'AI 연구원': [
            '논문', 'paper', 'research', '연구', 'SOTA',
            'state-of-the-art', 'novel', 'benchmark',
            'ablation', 'experiment', '실험',
        ],
        '백엔드 개발자': [
            'REST API', 'API 개발', 'API 설계', '서버 개발',
            'spring', 'django', 'fastapi', 'node.js',
            'microservice', 'MSA', '데이터베이스 설계',
        ],
        '프론트엔드 개발자': [
            'react', 'vue', 'angular', 'next.js', 'typescript',
            'CSS', 'HTML', 'UI/UX', '웹 프론트',
            'SPA', 'SSR', '컴포넌트',
        ],
        '풀스택 개발자': [
            'fullstack', 'full-stack', '프론트엔드와 백엔드',
            'frontend and backend', '웹 애플리케이션 전체',
        ],
    }

    def normalize_position_with_body(self, position: str, body_text: str) -> NormalizationResult:
        """
        직무명 + 본문 텍스트를 활용한 고도화된 정규화

        Args:
            position: 원본 직무명
            body_text: 채용공고 본문 텍스트

        Returns:
            NormalizationResult: 정규화 결과
        """
        # 1. 기존 직무명 기반 정규화 실행
        title_result = self.normalize_position(position)

        # 2. confidence >= 0.8이면 즉시 반환
        if title_result.confidence >= 0.8:
            return title_result

        # 3. 본문 키워드 기반 매칭
        body_result = self._match_by_body(position, body_text)

        # 4. 둘 중 높은 confidence 결과 반환
        if body_result and body_result.confidence > title_result.confidence:
            return body_result

        return title_result

    def _match_by_body(self, position: str, body_text: str) -> Optional[NormalizationResult]:
        """본문 키워드 기반 직무 추론"""
        if not body_text or not body_text.strip():
            return None

        lower_text = body_text.lower()
        best_match = None
        best_count = 0

        for standard_name, keywords in self.BODY_KEYWORD_RULES.items():
            match_count = sum(1 for kw in keywords if kw.lower() in lower_text)
            if match_count > best_count:
                best_count = match_count
                best_match = standard_name

        if best_match and best_count >= 2:
            confidence = 0.7 if best_count >= 3 else 0.6
            return NormalizationResult(
                raw_title=position,
                clean_title=self._clean_job_title(position),
                standardized_title=best_match,
                confidence=confidence,
                matching_method="body_keyword_match",
                manual_review=confidence < self.confidence_threshold,
            )

        return None

    def batch_normalize(self, positions: List[str]) -> List[NormalizationResult]:
        """
        여러 직무명을 일괄 정규화
        
        Args:
            positions (List[str]): 직무명 리스트
            
        Returns:
            List[NormalizationResult]: 정규화 결과 리스트
        """
        return [self.normalize_position(position) for position in positions]
    
    def get_standardized_value(self, position: str) -> Optional[str]:
        """
        직무명에 대한 표준화된 값만 반환 (DB 저장용)
        
        Args:
            position (str): 원본 직무명
            
        Returns:
            Optional[str]: 표준화된 직무명 (신뢰도가 높은 경우만)
        """
        result = self.normalize_position(position)
        
        # 신뢰도가 임계값 이상인 경우만 표준화된 값 반환
        if result.confidence >= self.confidence_threshold:
            return result.standardized_title
        
        # 신뢰도가 낮은 경우 None 반환 (수동 검토 필요)
        return None