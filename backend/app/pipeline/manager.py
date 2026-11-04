import time 
from datetime import datetime
from typing import List, Optional, Callable
from app.pipeline.stages.url_collector import URLCollectorStage
from app.pipeline.stages.url_validator import URLValidatorStage
from app.pipeline.stages.content_scraper import ContentScraperStage
from app.pipeline.stages.normalizer import JobNormalizerStage
from app.pipeline.stages.database_saver import DatabaseSaverStage
from app.pipeline.stages.file_saver import LocalFileSaverStage
from app.pipeline.data_models import (
    JobDetails,
    JobPostingData,
    JobSaveResult,
    PipelineConfig,
    PipelineMetrics,
    StageResult,
    ValidatedURL,
)
from app.core.logging import create_development_logger


def decide_batch_status(saved: int, failed: int, stage_error: bool) -> str:
    """실행 결과로 배치 상태를 정한다.

    Args:
        saved: 실제 저장한 공고 수.
        failed: 상세 추출 실패와 저장 실패를 합친 공고 수.
        stage_error: URL 수집 스테이지가 실패했거나 카드를 하나도 읽지 못했는지.

    Returns:
        실패가 없으면 `completed` (신규 0건 포함), 실패가 있어도 저장한 공고가
        있으면 `partial`, 저장한 공고가 없으면 `failed`.
    """
    if not failed and not stage_error:
        return "completed"
    return "partial" if saved > 0 else "failed"


class PipelineManager:
    """🔄 교대 처리용 Pipeline 관리자 - 스크롤-검증 사이클"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = create_development_logger(__name__)
        self.metrics = PipelineMetrics()
        self.batch_id = None
        self.status = None

        # Stage들 초기화
        self.url_collector = URLCollectorStage()
        self.url_validator = URLValidatorStage(batch_size=config.batch_size)
        self.content_scraper = ContentScraperStage(config=config, batch_size=config.batch_size)
        self.job_normalizer = JobNormalizerStage()
        self.database_saver = DatabaseSaverStage() if config.save_to_database else None
        self.local_file_saver = LocalFileSaverStage() if config.save_to_local else None

        # 결과 저장 관리
        self.total_validated_count = 0  # 검증된 URL 카운트
        self.total_job_details_count = 0  # 상세정보 스크래핑 카운트
        self.total_collected_count = 0  # 수집된 URL 카운트
        self.total_filtered_count = 0  # DB 조기 필터링으로 제외된 카운트
        self._stage_error = False  # URL 수집 · 검증 스테이지 자체의 실패

        # DB 조기 필터링용 기존 posting_id 캐시
        self._existing_posting_ids: set = set()

        self.logger.info(f"🔄 Interactive Pipeline initialized for job: {config.job}")

    def _load_existing_posting_ids(self):
        """DB에서 기존 posting_id 목록을 일괄 로드하여 캐시"""
        try:
            from app.core.database import db_manager
            from app.models import JobPosting

            if not db_manager._initialized:
                db_manager.initialize()

            with db_manager.get_session() as session:
                rows = session.query(JobPosting.posting_id).all()
                self._existing_posting_ids = {row.posting_id for row in rows}
                self.logger.info(
                    f"📦 Loaded {len(self._existing_posting_ids)} existing posting IDs from DB"
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load existing posting IDs: {e}")
            self._existing_posting_ids = set()

    def _filter_new_postings(
        self, job_posts: List[JobPostingData]
    ) -> List[JobPostingData]:
        """DB에 이미 존재하는 posting_id를 제외하고 신규 공고만 반환"""
        if not self._existing_posting_ids:
            return job_posts

        new_posts = [
            p for p in job_posts
            if p.posting_id not in self._existing_posting_ids
        ]
        filtered = len(job_posts) - len(new_posts)
        self.total_filtered_count += filtered

        if filtered > 0:
            self.logger.info(
                f"🔍 DB 조기 필터링: {len(job_posts)}건 중 {filtered}건 기존, "
                f"{len(new_posts)}건 신규"
            )
        return new_posts
    
    async def run(self, save_callback: Optional[Callable] = None) -> PipelineMetrics:
        """🚀 교대 처리 파이프라인 실행"""
        start_time = time.time()
        
        # 데이터베이스 저장이 활성화된 경우에만 배치 생성
        if self.database_saver:
            job = self.config.job 
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_name = f"{job}_{timestamp}"
            self.database_saver.create_batch(batch_name=batch_name, 
                                             scraper_type=self.config.scraper_type)
        
        mode = self.config.scrape_mode
        mode_desc = {
            "default": f"기본 (최대 {self.config.max_scrolls}회 스크롤)",
            "incremental": "증분 수집 (신규 없으면 조기 종료)",
            "full": "전체 수집 (페이지 끝까지)",
        }
        self.logger.info("🚀 Starting Interactive Pipeline execution...")
        self.logger.info(f"📋 Config: Job={self.config.job}, Mode={mode_desc.get(mode, mode)}")

        # DB 기존 posting_id 로드 (조기 필터링용)
        if self.config.save_to_database:
            self._load_existing_posting_ids()

        scroll_count = 0
        low_yield_count = 0  # 신규 비율 10% 미만인 연속 스크롤 횟수

        try:
            self.logger.info("🔄 Starting scroll-validate cycle...")
            
            max_scrolls = self.config.max_scrolls if mode != "full" else 999999
            while scroll_count < max_scrolls:
                cycle_start = time.time()
                self.logger.info(f"🔄 Scroll cycle {scroll_count + 1}/{self.config.max_scrolls}")
                
                # [Stage 1] URL 수집 (스크롤 1회) 
                
                # collect task 생성 (데이터베이스 저장 시에만)
                url_task_id = None
                if self.database_saver and self.database_saver.batch_id: 
                    url_task_id = self.database_saver.create_task(self.url_collector.name)
                
                # collect url 스테이지 실행 
                collect_result = await self._collect_urls()
                
                # collect task 업데이트 (데이터베이스 저장 시에만)
                if url_task_id and self.database_saver:
                    if collect_result.success: 
                        self.database_saver.update_task_status(task_id=url_task_id, 
                                                               status='completed',
                                                               success_count=collect_result.urls_processed,
                                                               fail_count=collect_result.urls_failed,
                                                               error_message=None,
                                                               duration=collect_result.execution_time)
                        self.logger.info("✅ URL task 생성 완료")
                    else:
                        self.database_saver.update_task_status(task_id=url_task_id, 
                                                               status='failed',
                                                               success_count=0,
                                                               fail_count=collect_result.urls_failed,
                                                               error_message=collect_result.error_message,
                                                               duration=collect_result.execution_time)
                
                self.metrics.add_stage_result(collect_result)
                self.metrics.failed_cards += collect_result.urls_failed

                if not collect_result.success:
                    self.logger.error("❌ URL 수집 실패. 파이프라인 종료.")
                    self._stage_error = True
                    break
                
                new_job_posts = collect_result.data
                if not new_job_posts:
                    self.logger.info("🚦 더 이상 새로운 URL이 없습니다. 파이프라인을 종료합니다.")
                    break

                collected_before_filter = len(new_job_posts)
                self.total_collected_count += collected_before_filter
                self.metrics.total_urls_collected += collected_before_filter

                # [Stage 1.5] DB 조기 필터링 — 이미 수집된 공고 제외
                new_job_posts = self._filter_new_postings(new_job_posts)
                new_count = len(new_job_posts)

                # Incremental 모드: 신규 비율 기반 조기 종료
                if mode == "incremental" and collected_before_filter > 0:
                    new_ratio = new_count / collected_before_filter
                    if new_ratio < 0.1:
                        low_yield_count += 1
                        self.logger.info(
                            f"🔍 신규 비율 {new_ratio:.0%} (< 10%) — "
                            f"low yield 연속 {low_yield_count}회"
                        )
                        if low_yield_count >= 2:
                            self.logger.info(
                                "⏹️ 연속 2회 low yield → 조기 종료 (Incremental)"
                            )
                            break
                    else:
                        low_yield_count = 0

                if not new_job_posts:
                    scroll_count += 1
                    continue

                # [Stage 2] URL 검증
                
                #  validate task 생성 (데이터베이스 저장 시에만)
                validate_task_id = None
                if self.database_saver:
                    validate_task_id = self.database_saver.create_task(self.url_validator.name)          
                
                # URL 검증 스테이지 실행
                validate_result = await self._validate_urls(new_job_posts)
                self._record_validation(validate_result)

                # validate task 업데이트 (데이터베이스 저장 시에만)
                if validate_result.success:
                    if validate_task_id and self.database_saver:
                        self.database_saver.update_task_status(
                            task_id=validate_task_id,
                            status='completed',
                            success_count=validate_result.urls_processed,
                            fail_count=validate_result.urls_failed,
                            duration=validate_result.execution_time,
                            error_message=None
                        )
                        self.logger.info("✅ URL 검증 task 완료")

                    # 결과 저장 및 DB 저장
                    validated_urls = validate_result.data
                    self.total_validated_count += len(validated_urls)

                    # 검증된 URL을 데이터베이스에 저장
                    if self.database_saver:
                        try:
                            url_save_result = await self.database_saver.execute(validated_urls)
                            if url_save_result.success:
                                self.logger.info(f"💾 Saved {url_save_result.urls_processed} URLs to database")
                            else:
                                self.logger.error(f"❌ Database save (URLs) failed: {url_save_result.error_message}")
                        except Exception as e:
                            self.logger.error(f"❌ Database save (URLs) failed: {e}")

                else:
                    if validate_task_id and self.database_saver:
                        self.database_saver.update_task_status(
                            task_id=validate_task_id,
                            status='failed',
                            success_count=0,
                            fail_count=validate_result.urls_processed if validate_result.urls_processed else len(new_job_posts),
                            duration=validate_result.execution_time,
                            error_message=validate_result.error_message
                        )
                    self.logger.warning("⚠️ URL 검증에서 문제가 발생했습니다.")
                    self._stage_error = True
                    scroll_count += 1
                    continue
                
                # [Stage 3] 직무 상세 정보 스크래핑 (유효한 URL만)
                valid_urls = [url for url in validated_urls if url.is_valid]
                if valid_urls:
                    self.logger.info(f"📄 Scraping content for {len(valid_urls)} valid URLs...")
                    
                    # content scraping task 생성 (데이터베이스 저장 시에만)
                    scraping_task_id = None
                    if self.database_saver:
                        scraping_task_id = self.database_saver.create_task(self.content_scraper.name)
                    
                    try:
                        # 컨텐츠 스크래핑 스테이지 실행
                        scrape_result = await self._scrape_content(valid_urls)
                        
                        # scraping task 업데이트
                        if scrape_result.success and scrape_result.data:
                            # [Stage 4] 직무명 정규화 (스크래핑 성공한 데이터에 대해서만)
                            self.logger.info(f"🎯 Starting job normalization for {len(scrape_result.data)} scraped items...")
                            
                            # 정규화 task 생성 (데이터베이스 저장 시에만)
                            normalization_task_id = None
                            if self.database_saver:
                                normalization_task_id = self.database_saver.create_task(self.job_normalizer.name)
                            
                            try:
                                # 정규화 스테이지 실행
                                normalize_result = await self._normalize_jobs(scrape_result.data)
                                
                                if normalize_result.success and normalize_result.data:
                                    # 정규화 task 완료 처리 (데이터베이스 저장 시에만)
                                    if normalization_task_id and self.database_saver:
                                        self.database_saver.update_task_status(
                                            task_id=normalization_task_id,
                                            status='completed',
                                            success_count=normalize_result.urls_processed,
                                            fail_count=normalize_result.urls_failed,
                                            duration=normalize_result.execution_time,
                                            error_message=None
                                        )
                                    self.logger.info(f"✅ Job normalization completed: {normalize_result.urls_processed} items processed")
                                    
                                    # 정규화된 데이터를 사용
                                    job_details = normalize_result.data
                                else:
                                    # 정규화 실패 시 원본 데이터 사용
                                    if normalization_task_id and self.database_saver:
                                        self.database_saver.update_task_status(
                                            task_id=normalization_task_id,
                                            status='failed',
                                            success_count=0,
                                            fail_count=len(scrape_result.data),
                                            duration=normalize_result.execution_time if normalize_result else 0,
                                            error_message=normalize_result.error_message if normalize_result else "Normalization failed"
                                        )
                                    self.logger.warning("⚠️ Job normalization failed, using original data")
                                    job_details = scrape_result.data
                                    
                            except Exception as e:
                                # 정규화 예외 발생 시 원본 데이터 사용
                                if normalization_task_id and self.database_saver:
                                    self.database_saver.update_task_status(
                                        task_id=normalization_task_id,
                                        status='failed',
                                        success_count=0,
                                        fail_count=len(scrape_result.data),
                                        duration=0,
                                        error_message=str(e)
                                    )
                                self.logger.error(f"❌ Job normalization error: {e}", exc_info=True)
                                job_details = scrape_result.data
                            self.total_job_details_count += len(job_details)
                            
                            # Task 완료 처리 - 성공/실패 개수 계산
                            failed_details = [detail for detail in job_details if not detail.success]
                            successful_scrapes = len(job_details) - len(failed_details)
                            failed_scrapes = len(valid_urls) - successful_scrapes
                            self.metrics.successful_scrapes += successful_scrapes
                            self.metrics.failed_scrapes += failed_scrapes
                            self.metrics.failed_count += failed_scrapes
                            if self.database_saver:
                                self.database_saver.record_failures(failed_details)
                            
                            # 성공률에 따른 상태 결정
                            if successful_scrapes > 0:
                                task_status = 'completed'
                                status_msg = f"✅ Content scraping task 완료: {successful_scrapes}/{len(job_details)} successful"
                            else:
                                task_status = 'failed'  
                                status_msg = f"❌ Content scraping task 실패: 모든 URL 스크래핑 실패"
                            
                            if scraping_task_id and self.database_saver:
                                self.database_saver.update_task_status(
                                    task_id=scraping_task_id,
                                    status=task_status,
                                    success_count=successful_scrapes,
                                    fail_count=failed_scrapes,
                                    duration=scrape_result.execution_time,
                                    error_message=failed_details[0].error_message if failed_details else None
                                )
                            self.logger.info(status_msg)
                            
                            # 데이터 저장 처리
                            if successful_scrapes > 0:
                                # 데이터베이스 저장
                                if self.database_saver:
                                    await self._save_job_details(job_details)
                                else:
                                    # DB 없이 돌릴 때는 파일 저장이 유일한 저장이다
                                    self.metrics.saved_count += successful_scrapes
                                
                                # 로컬 파일 저장
                                if self.local_file_saver:
                                    try:
                                        file_result = await self.local_file_saver.execute((job_details, self.config))
                                        self.metrics.file_save_failures += file_result.urls_failed
                                        if file_result.success and not file_result.urls_failed:
                                            self.logger.info(f"📁 Saved {successful_scrapes} job details to local file")
                                        else:
                                            self.logger.error(f"❌ Local file save failed: {file_result.urls_failed} items")
                                    except Exception as e:
                                        self.metrics.file_save_failures += len(job_details)
                                        self.logger.error(f"❌ Local file save failed: {e}")
                            
                            self.logger.info(f"📊 Content scraping: {successful_scrapes} successful, {failed_scrapes} failed out of {len(job_details)}")
                        else:
                            # 스크래핑 완전 실패 처리
                            if scraping_task_id and self.database_saver:
                                self.database_saver.update_task_status(
                                    task_id=scraping_task_id,
                                    status='failed',
                                    success_count=0,
                                    fail_count=len(valid_urls),
                                    duration=scrape_result.execution_time if scrape_result else 0,
                                    error_message=scrape_result.error_message if scrape_result else "Scraping failed with no result"
                                )
                            self.logger.warning(f"⚠️ Content scraping 완전 실패 - success: {scrape_result.success if scrape_result else False}")
                            self._record_scrape_stage_failure(
                                valid_urls,
                                (scrape_result.error_message if scrape_result else None) or "Scraping failed with no result",
                            )
                            
                    except Exception as e:
                        # 예외 발생 시 Task 실패 처리
                        if scraping_task_id and self.database_saver:
                            self.database_saver.update_task_status(
                                task_id=scraping_task_id,
                                status='failed',
                                success_count=0,
                                fail_count=len(valid_urls),
                                duration=0,
                                error_message=str(e)
                            )
                        self.logger.error(f"❌ Content scraping error: {e}", exc_info=True)
                        self._record_scrape_stage_failure(valid_urls, str(e))
                        
                else:
                    self.logger.info("📄 No valid URLs found for content scraping")
                
                cycle_time = time.time() - cycle_start
                valid_count = sum(1 for v in validated_urls if v.is_valid)
                
                self.logger.info(
                    f"✅ Cycle {scroll_count + 1} completed: "
                    f"{validate_result.urls_processed} processed, {valid_count} valid, "
                    f"{cycle_time:.2f}s"
                )
                
                scroll_count += 1
        
        except Exception as e:
            self.logger.error(f"❌ Pipeline execution failed: {e}", exc_info=True)
            # 에러 발생 시 배치를 failed로 업데이트
            self._finish_batch("failed")
            raise
        
        finally:
            # 리소스 정리
            await self.cleanup()
        
        # 카드가 있었는데 하나도 읽지 못했으면 수집이 깨진 것이다
        no_card_readable = self.metrics.failed_cards > 0 and self.total_collected_count == 0
        self._finish_batch(
            decide_batch_status(
                self.metrics.saved_count,
                self.metrics.failed_count,
                self._stage_error or no_card_readable,
            )
        )
        
        # 최종 메트릭 완료
        self.metrics.total_execution_time = time.time() - start_time
        self._log_final_metrics()
        
        return self.metrics
    
    async def _collect_urls(self) -> StageResult:
        """🌍 URL 수집 단계(URLCollectorStage)"""
        self.logger.debug("🔄 Executing URL collection...")
        return await self.url_collector.execute(self.config)
    
    async def _validate_urls(self, urls) -> StageResult:
        """✅ URL 검증 단계(URLValidatorStage)"""
        self.logger.debug(f"🔍 Validating {len(urls)} URLs...")
        return await self.url_validator.execute(urls)
    
    async def _scrape_content(self, validated_urls) -> StageResult:
        """📄 컨텐츠 스크래핑 단계(ContentScraperStage)"""
        self.logger.debug(f"📄 Scraping content for {len(validated_urls)} URLs...")
        return await self.content_scraper.execute(validated_urls)
    
    async def _normalize_jobs(self, scraped_data) -> StageResult:
        """🎯 직무명 정규화 단계(JobNormalizerStage)"""
        self.logger.debug(f"🎯 Normalizing jobs for {len(scraped_data)} items...")
        return await self.job_normalizer.execute(scraped_data)
    
    
    def _record_validation(self, validate_result: StageResult) -> None:
        """📊 URL 검증 결과를 메트릭에 더한다."""
        self.metrics.add_stage_result(validate_result)

        if validate_result.data:
            valid_count = sum(1 for url in validate_result.data if url.is_valid)
            self.metrics.valid_urls += valid_count
            self.metrics.invalid_urls += len(validate_result.data) - valid_count

    def _record_scrape_stage_failure(
        self, valid_urls: List[ValidatedURL], error_message: str
    ) -> None:
        """스크래핑 스테이지 전체가 실패했을 때 대상 공고를 모두 실패로 남긴다.

        Args:
            valid_urls: 스크래핑하려던 URL.
            error_message: 공고마다 남길 실패 원인.
        """
        self.metrics.failed_scrapes += len(valid_urls)
        self.metrics.failed_count += len(valid_urls)
        if self.database_saver:
            self.database_saver.record_failures(
                [
                    JobDetails(
                        job_url=url.job_url,
                        job_description={},
                        success=False,
                        error_message=error_message,
                    )
                    for url in valid_urls
                ]
            )

    async def _save_job_details(self, job_details: List[JobDetails]) -> None:
        """공고를 저장하고, 실제 저장 결과로만 건수와 캐시를 갱신한다.

        Args:
            job_details: 정규화까지 끝난 공고. 상세 추출 실패분은 저장하지 않는다.
        """
        saver = self.database_saver
        if saver is None:
            return

        try:
            stage_result = await saver.execute(job_details)
            error_message = None if stage_result.success else stage_result.error_message
        except Exception as e:
            stage_result = None
            error_message = str(e)

        if stage_result is not None and error_message is None:
            result = stage_result.data
        else:
            self.logger.error(f"❌ Database save (job details) failed: {error_message}")
            failed = [detail for detail in job_details if detail.success]
            for detail in failed:
                detail.error_message = f"DB 저장 실패: {error_message}"
            result = JobSaveResult(failed=failed)

        self.metrics.saved_count += len(result.saved)
        self.metrics.failed_count += len(result.failed)
        self._existing_posting_ids.update(
            detail.job_url.posting_id for detail in result.saved
        )
        saver.record_failures(result.failed)
        self.logger.info(
            f"💾 Saved {len(result.saved)} job details to database "
            f"({len(result.failed)} failed, {result.duplicates} duplicates)"
        )

    def _finish_batch(self, status: str) -> None:
        """최종 상태를 메트릭과 배치에 남긴다.

        Args:
            status: 배치 상태.
        """
        self.metrics.batch_status = status
        if self.database_saver and self.database_saver.batch_id:
            self.database_saver.update_batch_status(
                status,
                self.total_validated_count,
                collected=self.total_collected_count,
                saved=self.metrics.saved_count,
                failed=self.metrics.failed_count,
                skipped=self.metrics.skipped_count,
            )

    def _log_final_metrics(self):
        """📈 최종 통계 로깅"""
        new_count = self.total_collected_count - self.total_filtered_count
        efficiency = (
            f"{new_count}/{self.total_collected_count} "
            f"({new_count / self.total_collected_count * 100:.0f}%)"
            if self.total_collected_count > 0
            else "N/A"
        )

        self.logger.info("📊 Pipeline Execution Summary:")
        self.logger.info(f"   📎 URLs Collected: {self.total_collected_count}")
        self.logger.info(f"   🔍 DB Filtered (duplicates): {self.total_filtered_count}")
        self.logger.info(f"   🆕 New Postings: {efficiency}")
        self.logger.info(f"   ✅ Valid URLs: {self.metrics.valid_urls}")
        self.logger.info(f"   ❌ Invalid URLs: {self.metrics.invalid_urls}")
        self.logger.info(f"   📄 Job Details Scraped: {self.total_job_details_count}")
        self.logger.info(f"   💾 Saved: {self.metrics.saved_count}")
        self.logger.info(f"   ❌ Failed: {self.metrics.failed_count}")
        self.logger.info(f"   ⏭️ Skipped (retry limit): {self.metrics.skipped_count}")
        self.logger.info(f"   🃏 Failed Cards: {self.metrics.failed_cards}")
        self.logger.info(f"   📁 File Save Failures: {self.metrics.file_save_failures}")
        self.logger.info(f"   🏁 Batch Status: {self.metrics.batch_status}")
        self.logger.info(f"   ⏱️ Total Execution Time: {self.metrics.total_execution_time:.2f}s")
    
    async def cleanup(self):
        """🧹 리소스 정리"""
        self.logger.info("🧹 Cleaning up pipeline resources...")
        
        # 브라우저 세션 정리
        if self.url_collector:
            await self.url_collector.close_browser()
            self.logger.info("🔒 URL Collector browser session cleaned up")
        
        # 컨텐츠 스크래퍼 정리
        if self.content_scraper:
            await self.content_scraper.cleanup()
            self.logger.info("🔒 Content scraper cleaned up")
    