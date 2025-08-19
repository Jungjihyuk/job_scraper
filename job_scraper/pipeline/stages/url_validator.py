import time
from typing import List
import httpx

from job_scraper.pipeline.core.base_stage import AsyncBatchStage
from job_scraper.pipeline.core.data_models import JobPostingData, ValidatedURL


class URLValidatorStage(AsyncBatchStage):
    """✅ URL 검증 Stage - 병렬로 URL 유효성 검사"""
    
    def __init__(self, batch_size: int = 10):
        super().__init__("URLValidator", batch_size=batch_size)
        self.timeout = 10
        
    async def process_single_item(self, job_post: JobPostingData) -> ValidatedURL:
        """단일 URL 검증"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                
                self.logger.debug(f"🔍 Validating URL: {job_post.full_url}")
                
                # HEAD 요청으로 빠른 검증
                response = await client.head(job_post.full_url)
                response_time = time.time() - start_time
                
                is_valid = 200 <= response.status_code < 300
                
                validated_url = ValidatedURL(
                    job_url=job_post,
                    is_valid=is_valid,
                    status_code=response.status_code,
                    response_time=response_time
                )
                
                if is_valid:
                    self.logger.debug(
                        f"✅ Valid URL: {job_post.full_url} "
                        f"(Status: {response.status_code}, Time: {response_time:.2f}s)"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Invalid URL: {job_post.full_url} "
                        f"(Status: {response.status_code})"
                    )
                
                return validated_url
                
        except httpx.TimeoutException:
            response_time = time.time() - start_time
            error_msg = f"Timeout after {self.timeout}s"
            
            self.logger.warning(f"⏰ URL timeout: {job_post.full_url}")
            
            return ValidatedURL(
                job_url=job_post,
                is_valid=False,
                response_time=response_time,
                error_message=error_msg
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"❌ URL validation failed: {job_post.full_url} - {e}")
            
            return ValidatedURL(
                job_url=job_post,
                is_valid=False,
                response_time=response_time,
                error_message=error_msg
            )
    
    async def process(self, job_post: List[JobPostingData]) -> List[ValidatedURL]:
        """URL 목록 검증 (부모 클래스의 배치 처리 사용)"""
        self.logger.info(f"🔍 Validating {len(job_post)} URLs in batches of {self.batch_size}")
        
        # 부모 클래스의 배치 처리 실행
        validated_urls = await super().process(job_post)
        
        # 통계 출력
        valid_count = sum(1 for url in validated_urls if url.is_valid)
        invalid_count = len(validated_urls) - valid_count
        
        self.logger.info(
            f"✅ URL validation completed: "
            f"{valid_count} valid, {invalid_count} invalid"
        )
        
        return validated_urls