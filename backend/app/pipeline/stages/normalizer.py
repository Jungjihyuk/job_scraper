"""
Job normalization stage for the scraping pipeline.
"""
import asyncio
from typing import Dict, List, Any
from app.pipeline.stages.base import BaseStage
from app.pipeline.data_models import JobDetails
from app.pipeline.normalizers.job import JobNormalizer, NormalizationResult
from app.pipeline.normalizers.experience import ExperienceNormalizer, ExperienceNormalizationResult
from app.pipeline.normalizers.content import ContentAnalyzer
from app.core.logging import create_development_logger

class JobNormalizerStage(BaseStage):
    """
    스크래핑된 데이터의 직무명과 경력을 정규화하는 스테이지
    
    이 스테이지는 content_scraper 스테이지 다음, database_saver 스테이지 이전에 실행되어
    직무명(position)과 경력(experience)을 정규화하고 표준화된 값을 추가합니다.
    """
    
    def __init__(self, enable_duplicate_check: bool = False):
        super().__init__("JobNormalizer", enable_duplicate_check)
        self.job_normalizer = JobNormalizer()
        self.experience_normalizer = ExperienceNormalizer()
        self.content_analyzer = ContentAnalyzer()
        self.logger = create_development_logger("pipeline.JobNormalizer")
    
    async def process(self, data: List[JobDetails]) -> List[JobDetails]:
        """
        스크래핑된 직무 및 경력 데이터를 정규화 처리
        
        Args:
            data: content_scraper에서 전달받은 JobDetails 객체 리스트
            
        Returns:
            정규화된 직무 및 경력 정보가 추가된 JobDetails 객체 리스트
        """
        if not data:
            self.logger.warning("⚠️ No data received for normalization")
            return []
        
        normalized_data = []
        
        for job_details in data:
            try:
                # 직무명 정규화
                normalized_job_details = self._normalize_position(job_details)
                
                # 경력 정규화
                normalized_job_details = self._normalize_experience(normalized_job_details)

                # 콘텐츠 분석 (도메인 + 핵심 기술)
                normalized_job_details = self._analyze_content(normalized_job_details)

                normalized_data.append(normalized_job_details)
                self.update_metrics(processed=1)
                    
            except Exception as e:
                posting_id = getattr(job_details.job_url, 'posting_id', 'Unknown')
                self.logger.error(f"❌ Failed to normalize item {posting_id}: {e}")
                normalized_data.append(job_details)  # 실패한 경우 원본 데이터 유지
                self.update_metrics(failed=1)
        
        self.logger.info(
            f"🎯 Job & Experience normalization completed: {len(normalized_data)} items processed"
        )
        
        return normalized_data
    
    def _normalize_position(self, job_details: JobDetails) -> JobDetails:
        """
        직무명 정규화
        
        Args:
            job_details: 원본 JobDetails 객체
            
        Returns:
            직무명 정규화 정보가 추가된 JobDetails 객체
        """
        # 원본 position 값 확인 (JobDetails.job_url.position에서 가져옴)
        position = job_details.job_url.position
        if not position:
            posting_id = getattr(job_details.job_url, 'posting_id', 'Unknown')
            self.logger.warning(f"⚠️ No position found in item: {posting_id}")
            return job_details

        # 본문 텍스트 추출
        body_parts = []
        if job_details.job_description:
            for key in ("main_tasks", "requirements", "preferred"):
                text = job_details.job_description.get(key, "")
                if text:
                    body_parts.append(text)
        body_text = " ".join(body_parts)

        # 직무명 정규화 수행 (본문 fallback 포함)
        result = self.job_normalizer.normalize_position_with_body(position, body_text)
        
        # JobDetails 객체에 정규화 정보 저장 (job_description에 추가)
        if not job_details.job_description:
            job_details.job_description = {}
        
        job_details.job_description['position_normalization'] = {
            'raw_title': result.raw_title,
            'clean_title': result.clean_title,
            'standardized_title': result.standardized_title,
            'confidence': result.confidence,
            'matching_method': result.matching_method,
            'manual_review': result.manual_review
        }
        
        # job_specialty 필드 추가 (DB 저장용, threshold 0.6으로 하향)
        specialty_threshold = 0.6
        if result.confidence >= specialty_threshold:
            job_details.job_description['job_specialty'] = result.standardized_title
        else:
            job_details.job_description['job_specialty'] = None

        # 로깅
        if result.confidence >= specialty_threshold:
            self.logger.debug(
                f"✅ Position normalized: '{position}' → '{result.standardized_title}' "
                f"(confidence: {result.confidence:.2f})"
            )
        else:
            self.logger.info(
                f"⚠️ Low confidence position normalization: '{position}' → '{result.standardized_title}' "
                f"(confidence: {result.confidence:.2f}, method: {result.matching_method})"
            )
        
        return job_details
    
    def _normalize_experience(self, job_details: JobDetails) -> JobDetails:
        """
        경력 정규화
        
        Args:
            job_details: JobDetails 객체 (직무명 정규화 완료)
            
        Returns:
            경력 정규화 정보가 추가된 JobDetails 객체
        """
        # 원본 experience 값 확인 (JobDetails.experience에서 가져옴)
        experience = job_details.experience
        if not experience:
            posting_id = getattr(job_details.job_url, 'posting_id', 'Unknown')
            self.logger.debug(f"No experience found in item: {posting_id}")
            return job_details
        
        # 경력 정규화 수행
        result = self.experience_normalizer.normalize_experience(experience)
        
        # JobDetails 객체에 정규화 정보 저장 (job_description에 추가)
        if not job_details.job_description:
            job_details.job_description = {}
        
        job_details.job_description['experience_normalization'] = {
            'raw_experience': result.raw_experience,
            'clean_experience': result.clean_experience,
            'standardized_experience': result.standardized_experience,
            'min_years': result.min_years,
            'max_years': result.max_years,
            'is_fresh_welcome': result.is_fresh_welcome,
            'confidence': result.confidence,
            'matching_method': result.matching_method,
            'manual_review': result.manual_review
        }
        
        # standardized_experience 필드 추가 (DB 저장용)
        if result.confidence >= self.experience_normalizer.confidence_threshold:
            job_details.job_description['standardized_experience'] = result.standardized_experience
        else:
            job_details.job_description['standardized_experience'] = None
        
        # 로깅
        if result.confidence >= self.experience_normalizer.confidence_threshold:
            self.logger.debug(
                f"✅ Experience normalized: '{experience}' → '{result.standardized_experience}' "
                f"(confidence: {result.confidence:.2f})"
            )
        else:
            self.logger.info(
                f"⚠️ Low confidence experience normalization: '{experience}' → '{result.standardized_experience}' "
                f"(confidence: {result.confidence:.2f})"
            )
        
        return job_details
    
    def _analyze_content(self, job_details: JobDetails) -> JobDetails:
        """
        본문에서 도메인 및 핵심 기술 추출

        Args:
            job_details: JobDetails 객체

        Returns:
            도메인/기술 정보가 추가된 JobDetails 객체
        """
        if not job_details.job_description:
            return job_details

        # main_tasks + requirements + preferred 결합
        parts = []
        for key in ("main_tasks", "requirements", "preferred"):
            text = job_details.job_description.get(key, "")
            if text:
                parts.append(text)

        body_text = " ".join(parts)
        if not body_text.strip():
            return job_details

        result = self.content_analyzer.analyze(body_text)

        if result.domain:
            job_details.job_description["domain"] = result.domain
        if result.core_technologies:
            job_details.job_description["core_technologies"] = result.core_technologies

        self.logger.debug(
            f"Content analysis: domain={result.domain}, "
            f"technologies={result.core_technologies}"
        )

        return job_details

    async def process_single_batch(self, batch: List[JobDetails]) -> List[JobDetails]:
        """
        배치 단위로 정규화 처리 (필요시 사용)
        
        Args:
            batch: JobDetails 배치 데이터
            
        Returns:
            정규화된 JobDetails 배치 데이터
        """
        return await self.process(batch)
    
    def get_normalization_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        정규화 통계 정보 생성
        
        Args:
            data: 정규화된 데이터
            
        Returns:
            통계 정보
        """
        if not data:
            return {}
        
        high_confidence_count = sum(
            1 for item in data 
            if item.get('normalization', {}).get('confidence', 0) >= self.job_normalizer.confidence_threshold
        )
        
        low_confidence_count = len(data) - high_confidence_count
        
        # 매칭 방법별 통계
        method_stats = {}
        for item in data:
            method = item.get('normalization', {}).get('matching_method', 'unknown')
            method_stats[method] = method_stats.get(method, 0) + 1
        
        # 표준 직무별 통계
        standardized_stats = {}
        for item in data:
            standardized = item.get('job_specialty')
            if standardized:
                standardized_stats[standardized] = standardized_stats.get(standardized, 0) + 1
        
        return {
            'total_items': len(data),
            'high_confidence': high_confidence_count,
            'low_confidence': low_confidence_count,
            'confidence_rate': high_confidence_count / len(data) if data else 0,
            'method_distribution': method_stats,
            'standardized_distribution': standardized_stats
        }