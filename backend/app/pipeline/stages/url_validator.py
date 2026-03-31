import asyncio
import time
from typing import List
import httpx

from app.pipeline.stages.base import AsyncBatchStage
from app.pipeline.data_models import JobPostingData, ValidatedURL

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 초, 재시도마다 2배씩 증가


class URLValidatorStage(AsyncBatchStage):
    """✅ URL 검증 Stage - 병렬로 URL 유효성 검사"""

    def __init__(self, batch_size: int = 10):
        super().__init__("URLValidator", batch_size=batch_size)
        self.timeout = 10

    async def process_single_item(self, job_post: JobPostingData) -> ValidatedURL:
        """단일 URL 검증 (일시적 오류 시 재시도)"""
        start_time = time.time()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True
                ) as client:

                    self.logger.debug(f"🔍 Validating URL: {job_post.full_url}")

                    response = await client.head(job_post.full_url)
                    response_time = time.time() - start_time

                    if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                        wait = RETRY_BACKOFF ** attempt
                        self.logger.warning(
                            f"⚠️ Retryable status {response.status_code} for {job_post.full_url} "
                            f"(attempt {attempt}/{MAX_RETRIES}, retrying in {wait}s)"
                        )
                        await asyncio.sleep(wait)
                        continue

                    is_valid = 200 <= response.status_code < 300

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

                    return ValidatedURL(
                        job_url=job_post,
                        is_valid=is_valid,
                        status_code=response.status_code,
                        response_time=response_time
                    )

            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF ** attempt
                    self.logger.warning(
                        f"⏰ URL timeout: {job_post.full_url} "
                        f"(attempt {attempt}/{MAX_RETRIES}, retrying in {wait}s)"
                    )
                    await asyncio.sleep(wait)
                    continue

                response_time = time.time() - start_time
                self.logger.warning(f"⏰ URL timeout after {MAX_RETRIES} attempts: {job_post.full_url}")
                return ValidatedURL(
                    job_url=job_post,
                    is_valid=False,
                    response_time=response_time,
                    error_message=f"Timeout after {MAX_RETRIES} attempts"
                )

            except Exception as e:
                response_time = time.time() - start_time
                self.logger.error(f"❌ URL validation failed: {job_post.full_url} - {e}")
                return ValidatedURL(
                    job_url=job_post,
                    is_valid=False,
                    response_time=response_time,
                    error_message=str(e)
                )

        # 모든 재시도 소진
        response_time = time.time() - start_time
        self.logger.warning(f"❌ URL invalid after {MAX_RETRIES} retries: {job_post.full_url}")
        return ValidatedURL(
            job_url=job_post,
            is_valid=False,
            response_time=response_time,
            error_message=f"Failed after {MAX_RETRIES} retries"
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