"""
Content analysis for domain, core technology, and job specialty extraction from job postings.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import yaml


@dataclass
class ContentAnalysisResult:
    """콘텐츠 분석 결과"""
    domain: Optional[str] = None
    domain_confidence: float = 0.0
    core_technologies: List[str] = field(default_factory=list)
    specialty_l1: Optional[str] = None
    specialty_l2: Optional[str] = None
    employment_type: Optional[str] = None
    analysis_method: str = "keyword_match"
    taxonomy_version: Optional[str] = None


class ContentAnalyzer:
    """채용공고 본문에서 산업 도메인과 핵심 기술을 추출하는 분석기"""

    DOMAIN_RULES: Dict[str, List[str]] = {
        "금융/핀테크": [
            "금융", "핀테크", "fintech", "은행", "증권", "보험", "결제", "payment",
            "투자", "자산관리", "뱅킹", "banking", "카드", "대출", "송금",
            "블록체인", "암호화폐", "가상자산", "디파이", "defi",
        ],
        "바이오/헬스케어": [
            "바이오", "헬스케어", "healthcare", "의료", "병원", "제약", "신약",
            "임상", "유전체", "genomics", "진단", "의약", "건강",
            "디지털헬스", "원격진료", "EMR", "PHR",
        ],
        "커머스/리테일": [
            "커머스", "이커머스", "e-commerce", "ecommerce", "쇼핑", "리테일",
            "retail", "상품", "주문", "배송", "물류", "풀필먼트",
            "마켓플레이스", "marketplace", "셀러", "입점",
        ],
        "게임": [
            "게임", "game", "gaming", "모바일게임", "PC게임", "콘솔",
            "게임서버", "게임엔진", "unity", "unreal", "게임개발",
            "라이브서비스", "게임운영",
        ],
        "콘텐츠/미디어": [
            "콘텐츠", "미디어", "media", "영상", "동영상", "스트리밍",
            "OTT", "음악", "웹툰", "만화", "출판", "뉴스",
            "크리에이터", "라이브", "방송",
        ],
        "SaaS/B2B": [
            "SaaS", "B2B", "기업용", "솔루션", "플랫폼", "ERP", "CRM",
            "그룹웨어", "협업", "워크플로우", "자동화", "엔터프라이즈",
            "enterprise", "API", "SDK",
        ],
        "교육/에듀테크": [
            "교육", "에듀테크", "edtech", "학습", "온라인교육", "LMS",
            "이러닝", "e-learning", "강의", "수강", "학원",
            "튜터", "커리큘럼",
        ],
        "모빌리티/자동차": [
            "모빌리티", "mobility", "자동차", "자율주행", "autonomous",
            "커넥티드카", "전기차", "EV", "라이드", "택시",
            "내비게이션", "지도", "map", "운송", "물류",
        ],
        "보안/사이버보안": [
            "보안", "사이버보안", "cybersecurity", "security", "정보보안",
            "취약점", "침해", "인증", "암호화", "방화벽",
            "SOC", "SIEM", "제로트러스트",
        ],
        "AI/딥테크": [
            "AI", "인공지능", "딥러닝", "deep learning", "머신러닝",
            "machine learning", "자연어처리", "NLP", "컴퓨터비전",
            "로보틱스", "robotics", "자동화", "LLM", "생성형",
        ],
    }

    TECH_RULES: Dict[str, List[str]] = {
        "RAG": [
            "RAG", "retrieval augmented", "retrieval-augmented",
            "벡터검색", "vector search", "vector db", "embedding",
            "임베딩", "지식베이스", "knowledge base",
        ],
        "LLM": [
            "LLM", "large language model", "GPT", "ChatGPT", "Claude",
            "생성형 AI", "generative AI", "프롬프트", "prompt",
            "파인튜닝", "fine-tuning", "finetuning", "RLHF",
        ],
        "Agent": [
            "agent", "에이전트", "agentic", "tool use",
            "function calling", "autonomous", "자율",
            "멀티에이전트", "multi-agent",
        ],
        "MLOps": [
            "MLOps", "ML ops", "모델 배포", "model serving",
            "모델 관리", "model registry", "feature store",
            "kubeflow", "mlflow", "airflow", "파이프라인",
        ],
        "Computer Vision": [
            "computer vision", "컴퓨터 비전", "컴퓨터비전",
            "영상처리", "이미지", "image", "객체 탐지", "object detection",
            "segmentation", "OCR", "얼굴인식",
        ],
        "NLP": [
            "NLP", "자연어처리", "자연어 처리", "natural language",
            "텍스트 분석", "text mining", "감성분석", "형태소",
            "토크나이저", "tokenizer", "번역", "요약",
        ],
        "Data Engineering": [
            "데이터 엔지니어링", "data engineering", "ETL", "ELT",
            "데이터 파이프라인", "data pipeline", "spark", "kafka",
            "hadoop", "데이터 웨어하우스", "data warehouse",
            "데이터 레이크", "data lake", "dbt",
        ],
        "Cloud/Infra": [
            "AWS", "GCP", "Azure", "클라우드", "cloud",
            "kubernetes", "k8s", "docker", "terraform",
            "인프라", "infrastructure", "DevOps", "CI/CD",
        ],
        "Recommendation": [
            "추천", "recommendation", "추천시스템", "recommender",
            "협업 필터링", "collaborative filtering",
            "개인화", "personalization", "CTR", "랭킹",
        ],
        "Search": [
            "검색", "search", "elasticsearch", "opensearch",
            "검색엔진", "search engine", "색인", "indexing",
            "쿼리", "query", "relevance", "ranking",
        ],
    }

    EMPLOYMENT_PATTERNS = {
        "프리랜서": [
            re.compile(r"\[프리랜서\]", re.IGNORECASE),
            re.compile(r"\[프리\]", re.IGNORECASE),
            re.compile(r"프리랜서", re.IGNORECASE),
            re.compile(r"freelance", re.IGNORECASE),
        ],
        "인턴": [
            re.compile(r"\[인턴\]", re.IGNORECASE),
            re.compile(r"인턴십", re.IGNORECASE),
            re.compile(r"intern", re.IGNORECASE),
        ],
        "계약직": [
            re.compile(r"계약직", re.IGNORECASE),
            re.compile(r"기간제", re.IGNORECASE),
            re.compile(r"contract", re.IGNORECASE),
        ],
    }

    def __init__(self):
        """ContentAnalyzer 초기화. TaxonomyManager가 있으면 버전을 추적."""
        self._taxonomy_version = None
        try:
            from app.services.taxonomy import get_taxonomy_manager
            mgr = get_taxonomy_manager()
            self._taxonomy_version = mgr.get_version("domain")
        except Exception:
            pass
        self._specialty_rules = self._load_specialty_taxonomy()

    def _load_specialty_taxonomy(self) -> Dict:
        """job_specialty.yaml에서 키워드 규칙을 로드"""
        yaml_path = (
            Path(__file__).resolve().parents[4]
            / "label_studio" / "taxonomy" / "job_specialty.yaml"
        )
        if not yaml_path.exists():
            return {}
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # 가중치 상수
    STRONG_WEIGHT = 3
    NORMAL_WEIGHT = 1
    TITLE_MULTIPLIER = 2

    def classify_specialty(
        self, position: str, body_text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        position(제목)과 본문으로 직무 대분류(l1)/소분류(l2)를 결정.

        가중치 규칙:
          - strong_keywords 매치: 3점
          - keywords 매치: 1점
          - 제목에서 매치된 키워드: 점수 2배
        """
        if not self._specialty_rules:
            return None, None

        categories = self._specialty_rules.get("categories", {})
        title_lower = position.lower()
        body_lower = body_text.lower()

        best_l1 = None
        best_l2 = None
        best_score = 0.0

        for l1_name, l1_data in categories.items():
            subcategories = l1_data.get("subcategories", {})
            for l2_name, l2_data in subcategories.items():
                score = 0.0

                for kw in l2_data.get("strong_keywords", []):
                    kw_lower = kw.lower()
                    if kw_lower in title_lower:
                        score += self.STRONG_WEIGHT * self.TITLE_MULTIPLIER
                    elif kw_lower in body_lower:
                        score += self.STRONG_WEIGHT

                for kw in l2_data.get("keywords", []):
                    kw_lower = kw.lower()
                    if kw_lower in title_lower:
                        score += self.NORMAL_WEIGHT * self.TITLE_MULTIPLIER
                    elif kw_lower in body_lower:
                        score += self.NORMAL_WEIGHT

                if score > best_score:
                    best_score = score
                    best_l1 = l1_name
                    best_l2 = l2_name

        # 최소 임계값: strong 1개(3점) 이상이거나 일반 3개(3점) 이상
        if best_score >= 3:
            return best_l1, best_l2
        return None, None

    def classify_employment_type(self, position: str) -> str:
        """position(제목)에서 고용형태를 추출. 기본값은 '정규직'."""
        for emp_type, patterns in self.EMPLOYMENT_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(position):
                    return emp_type
        return "정규직"

    def analyze(
        self, body_text: str, position: str = ""
    ) -> ContentAnalysisResult:
        """
        본문 텍스트에서 도메인, 핵심 기술, 직무 분류, 고용형태를 추출

        Args:
            body_text: 채용공고 본문 텍스트 (main_tasks + requirements + preferred 등)
            position: 채용공고 제목 (직무/고용형태 분류에 사용)

        Returns:
            ContentAnalysisResult: 분석 결과
        """
        if not body_text or not body_text.strip():
            return ContentAnalysisResult(
                employment_type=self.classify_employment_type(position) if position else None,
            )

        lower_text = body_text.lower()

        # 도메인 추출: 키워드 매치 수 최대인 도메인 선택 (최소 2개 매치 필요)
        domain = None
        domain_confidence = 0.0
        best_match_count = 0

        for domain_name, keywords in self.DOMAIN_RULES.items():
            match_count = sum(
                1 for kw in keywords if kw.lower() in lower_text
            )
            if match_count >= 2 and match_count > best_match_count:
                best_match_count = match_count
                domain = domain_name
                domain_confidence = min(0.5 + match_count * 0.1, 1.0)

        # 기술 추출: 각 기술별 키워드 매치 있으면 리스트에 추가
        core_technologies = []
        for tech_name, keywords in self.TECH_RULES.items():
            for kw in keywords:
                if kw.lower() in lower_text:
                    core_technologies.append(tech_name)
                    break

        # 직무 분류 (specialty)
        specialty_l1, specialty_l2 = self.classify_specialty(position, body_text)

        # 고용형태
        employment_type = self.classify_employment_type(position)

        return ContentAnalysisResult(
            domain=domain,
            domain_confidence=domain_confidence,
            core_technologies=core_technologies,
            specialty_l1=specialty_l1,
            specialty_l2=specialty_l2,
            employment_type=employment_type,
            analysis_method="keyword_match",
            taxonomy_version=self._taxonomy_version,
        )
