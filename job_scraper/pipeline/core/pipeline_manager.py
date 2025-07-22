import time 
from datetime import datetime
from typing import List, Optional, Callable
from job_scraper.pipeline.stages.url_collector import URLCollectorStage
from job_scraper.pipeline.stages.url_validator import URLValidatorStage
from job_scraper.pipeline.stages.content_scraper import ContentScraperStage
from job_scraper.pipeline.stages.database_saver import DatabaseSaverStage
from job_scraper.pipeline.core.data_models import PipelineConfig, PipelineMetrics, StageResult
from job_scraper.config.logging_config import create_development_logger


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
        self.url_validator = URLValidatorStage(batch_size=config.bacth_size)
        self.content_scraper = ContentScraperStage(config=config, batch_size=config.bacth_size)  # 병렬 처리로 배치 크기 증가
        self.database_saver = DatabaseSaverStage()
        
        # 결과 저장 관리
        self.total_validated_count = 0  # 검증된 URL 카운트
        self.total_job_details_count = 0  # 상세정보 스크래핑 카운트
        
        self.logger.info(f"🔄 Interactive Pipeline initialized for job: {config.job}")
    
    async def run(self, save_callback: Optional[Callable] = None) -> PipelineMetrics:
        """🚀 교대 처리 파이프라인 실행"""
        start_time = time.time()
        
        # 배치 테이블 생성 (항상 새 배치 생성)
        job = self.config.job 
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_name = f"{job}_{timestamp}"
        self.database_saver.create_batch(batch_name=batch_name, 
                                         scraper_type=self.config.scraper_type)
        
        self.logger.info("🚀 Starting Interactive Pipeline execution...")
        self.logger.info(f"📋 Config: Job={self.config.job}, Max Scrolls={self.config.max_scrolls}")
        
        scroll_count = 0
        
        try:
            self.logger.info("🔄 Starting scroll-validate cycle...")
            
            while scroll_count < self.config.max_scrolls:
                cycle_start = time.time()
                self.logger.info(f"🔄 Scroll cycle {scroll_count + 1}/{self.config.max_scrolls}")
                
                # [Stage 1] URL 수집 (스크롤 1회) 
                
                # collect task 생성
                if self.database_saver.batch_id: 
                    url_task_id = self.database_saver.create_task(self.url_collector.name, 0)  # 수집 전이므로 0
                else: 
                    self.logger.error("❌ Batch 생성 필요")
                    break 
                
                # collect url 스테이지 실행 
                collect_result = await self._collect_urls()
                
                # collect task 업데이트 
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
                    self.logger.error("❌ URL 수집 실패. 파이프라인 종료.")
                    break
                
                new_job_posts = collect_result.data
                if not new_job_posts:
                    self.logger.info("🚦 더 이상 새로운 URL이 없습니다. 파이프라인을 종료합니다.")
                    break
                
                                
                # [Stage 2] URL 검증
                
                #  validate task 생성 
                validate_task_id = self.database_saver.create_task(self.url_validator.name, len(new_job_posts))          
                
                # URL 검증 스테이지 실행
                validate_result = await self._validate_urls(new_job_posts)

                # validate task 업데이트
                if validate_result.success:
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
                    try:
                        await self.database_saver.execute(validated_urls)
                        self.logger.info(f"💾 Saved {len(validated_urls)} URLs to database")
                    except Exception as e:
                        self.logger.error(f"❌ Database save (URLs) failed: {e}")

                else:
                    self.database_saver.update_task_status(
                        task_id=validate_task_id,
                        status='failed',
                        success_count=0,
                        fail_count=validate_result.urls_processed if validate_result.urls_processed else len(new_job_posts),
                        duration=validate_result.execution_time,
                        error_message=validate_result.error_message
                    )
                    self.logger.warning("⚠️ URL 검증에서 문제가 발생했습니다.")
                    scroll_count += 1
                    continue
                
                # [Stage 3] 직무 상세 정보 스크래핑 (유효한 URL만)
                valid_urls = [url for url in validated_urls if url.is_valid]
                if valid_urls:
                    self.logger.info(f"📄 Scraping content for {len(valid_urls)} valid URLs...")
                    
                    # content scraping task 생성
                    scraping_task_id = self.database_saver.create_task(self.content_scraper.name, len(valid_urls))
                    
                    try:
                        # 컨텐츠 스크래핑 스테이지 실행
                        scrape_result = await self._scrape_content(valid_urls)
                        
                        # scraping task 업데이트
                        if scrape_result.success and scrape_result.data:
                            job_details = scrape_result.data
                            self.total_job_details_count += len(job_details)
                            
                            # Task 완료 처리 - 성공/실패 개수 계산
                            successful_scrapes = sum(1 for detail in job_details if detail.success)
                            failed_scrapes = len(job_details) - successful_scrapes
                            
                            # 성공률에 따른 상태 결정
                            if successful_scrapes > 0:
                                task_status = 'completed'
                                status_msg = f"✅ Content scraping task 완료: {successful_scrapes}/{len(job_details)} successful"
                            else:
                                task_status = 'failed'  
                                status_msg = f"❌ Content scraping task 실패: 모든 URL 스크래핑 실패"
                            
                            self.database_saver.update_task_status(
                                task_id=scraping_task_id,
                                status=task_status,
                                success_count=successful_scrapes,
                                fail_count=failed_scrapes,
                                duration=scrape_result.execution_time,
                                error_message=scrape_result.error_message if failed_scrapes > 0 else None
                            )
                            self.logger.info(status_msg)
                            
                            # 성공한 것들만 데이터베이스에 저장
                            if successful_scrapes > 0:
                                try:
                                    await self.database_saver.execute(job_details)
                                    self.logger.info(f"💾 Saved {successful_scrapes} job details to database")
                                except Exception as e:
                                    self.logger.error(f"❌ Database save (job details) failed: {e}")
                            
                            self.logger.info(f"📊 Content scraping: {successful_scrapes} successful, {failed_scrapes} failed out of {len(job_details)}")
                        else:
                            # 스크래핑 완전 실패 처리
                            self.database_saver.update_task_status(
                                task_id=scraping_task_id,
                                status='failed',
                                success_count=0,
                                fail_count=len(valid_urls),
                                duration=scrape_result.execution_time if scrape_result else 0,
                                error_message=scrape_result.error_message if scrape_result else "Scraping failed with no result"
                            )
                            self.logger.warning(f"⚠️ Content scraping 완전 실패 - success: {scrape_result.success if scrape_result else False}")
                            
                    except Exception as e:
                        # 예외 발생 시 Task 실패 처리
                        self.database_saver.update_task_status(
                            task_id=scraping_task_id,
                            status='failed',
                            success_count=0,
                            fail_count=len(valid_urls),
                            duration=0,
                            error_message=str(e)
                        )
                        self.logger.error(f"❌ Content scraping error: {e}", exc_info=True)
                        
                else:
                    self.logger.info("📄 No valid URLs found for content scraping")
                
                # 5. 메트릭 업데이트
                self._update_metrics(collect_result, validate_result)
                
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
            if self.database_saver.batch_id:
                self.database_saver.update_batch_status("failed", self.total_validated_count)
            raise
        
        finally:
            # 리소스 정리
            await self.cleanup()
        
        # 정상 완료 시 배치를 completed로 업데이트
        if self.database_saver.batch_id:
            self.database_saver.update_batch_status("completed", self.total_validated_count)
        
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
    
    
    def _update_metrics(self, collect_result: StageResult, validate_result: StageResult):
        """📊 메트릭 업데이트"""
        self.metrics.add_stage_result(collect_result)
        self.metrics.add_stage_result(validate_result)
        
        # URL 통계 업데이트
        self.metrics.total_urls_collected += collect_result.urls_processed
        
        if validate_result.data:
            valid_count = sum(1 for url in validate_result.data if url.is_valid)
            self.metrics.valid_urls += valid_count
            self.metrics.invalid_urls += len(validate_result.data) - valid_count
    
    def _log_final_metrics(self):
        """📈 최종 통계 로깅"""
        self.logger.info("📊 Interactive Pipeline Execution Summary:")
        self.logger.info(f"   📎 Total URLs Collected: {self.metrics.total_urls_collected}")
        self.logger.info(f"   ✅ Valid URLs: {self.metrics.valid_urls}")
        self.logger.info(f"   ❌ Invalid URLs: {self.metrics.invalid_urls}")
        self.logger.info(f"   ⏱️ Total Execution Time: {self.metrics.total_execution_time:.2f}s")
        self.logger.info(f"   🎯 Final Results: {self.total_validated_count} total validated URLs")
        self.logger.info(f"   📄 Job Details Scraped: {self.total_job_details_count} total job details")
    
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
    