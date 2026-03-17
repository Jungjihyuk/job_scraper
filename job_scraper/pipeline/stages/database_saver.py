"""
데이터베이스 저장 Stage
스크래핑된 데이터를 PostgreSQL에 저장
"""
import time
import hashlib
from typing import List, Union, Optional
from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from job_scraper.pipeline.core.base_stage import BaseStage
from job_scraper.pipeline.core.data_models import JobPostingData, ValidatedURL, JobDetails, StageResult
from job_scraper.database.connection import db_manager
from job_scraper.database.models import (
    ScrapingBatch, ScrapingTask, ScrapedUrl, 
    JobPosting, Company, JobCategory, Location
)
from job_scraper.utils.deadline_parser import DeadlineParser


class DatabaseSaverStage(BaseStage):
    """데이터베이스 저장 Stage"""
    
    def __init__(self):
        super().__init__("DatabaseSaver")
        self.deadline_parser = DeadlineParser()
        self.batch_id = None
        self.session_id = str(uuid4())[:8]
    
    async def process(self, data: Union[List[JobPostingData], List[ValidatedURL], List[JobDetails]]): # -> Union[List[ValidatedURL], List[JobDetails]]:
        """데이터를 데이터베이스에 저장"""
        if not data:
            self.logger.warning("📋 No data to save to database")
            return data
        
        # 데이터 타입 확인
    
        if isinstance(data[0], ValidatedURL): 
            return await self._save_validated_urls(data)
        elif isinstance(data[0], JobDetails):
            return await self._save_job_details(data)
        else:
            self.logger.error(f"❌ Unsupported data type: {type(data[0])}")
            return data
    
    def create_batch(self, batch_name: str, scraper_type: str) -> int: 
        """스크래핑 배치 생성 (매번 새 배치 생성)

        Args:
            batch_name (str): 파이프라인 배치를 구별할 수 있는 이름 
            scraper_type (str): 스크래핑할 사이트 이름 

        Returns:
            batch_id (int): 배치 테이블의 기본키 (id)
        """
        # 항상 새 배치 생성 (기존 배치 ID 무시)
        self.batch_id = None
        
        # 데이터베이스 연결 확인 및 초기화
        if not db_manager._initialized:
            self.logger.info("🔌 Initializing database connection...")
            if not db_manager.initialize():
                raise RuntimeError("Failed to initialize database connection")
        
        # 연결 테스트
        if not db_manager.test_connection():
            raise RuntimeError("Database connection test failed")
        
        try: 
            with db_manager.get_session() as session: 
                # 먼저 이전 실행의 미완료 배치들을 failed로 업데이트
                self._cleanup_incomplete_batches(session, scraper_type)
                
                batch = ScrapingBatch(
                    batch_name=f"{batch_name}_{self.session_id}",
                    scraper_type=scraper_type,
                    status="running",
                    total_urls = None,
                    started_at=datetime.now()
                )
                session.add(batch)
                session.commit()
                self.batch_id = batch.id
                self.logger.info(f"📝 Created main batch: {batch_name} ID: {self.batch_id}")
                return self.batch_id
                
        except Exception as e: 
            self.logger.error(f"❌ Failed to create main batch: {e}")       
            raise   
    
    def _cleanup_incomplete_batches(self, session: Session, scraper_type: str):
        """이전 실행의 미완료 배치들을 failed로 업데이트"""
        try:
            incomplete_batches = session.query(ScrapingBatch).filter_by(
                status="running",
                scraper_type=scraper_type
            ).all()
            
            if incomplete_batches:
                for batch in incomplete_batches:
                    batch.status = "failed"
                    batch.completed_at = datetime.now()
                
                session.commit()
                self.logger.info(f"🧹 Cleaned up {len(incomplete_batches)} incomplete batches")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to cleanup incomplete batches: {e}")
            # 정리 실패해도 새 배치 생성은 계속 진행
    
    def update_batch_status(self, status: str, total_urls: int): 
        """
        배치 상태 업데이트 
        """    
        if not self.batch_id: 
            return 
        
        try: 
            with db_manager.get_session() as session: 
                batch = session.query(ScrapingBatch).filter_by(id=self.batch_id).first()
                if batch: 
                    batch.status = status 
                    batch.total_urls = total_urls
                    
                    if status in ["completed", "failed"]:
                        batch.completed_at = datetime.now()
                    session.commit()
                    self.logger.info(f"📝 Updated batch status to: {status}") 
        except Exception as e: 
            self.logger.error(f"❌ Failed to update batch status: {e}") 
    
    def create_task(self, task_type: str) -> int: 
        """스크래핑 테스크 생성 (각 스테이지 별)

        Args:
            task_type (str): 스테이지 이름 

        Returns:
            int: 생성된 task의 ID
        """
        if not self.batch_id: 
            self.logger.warning("⚠️ No batch_id available for task creation")
            return None
        
        # 데이터베이스 연결 확인 및 초기화
        if not db_manager._initialized:
            self.logger.info("🔌 Initializing database connection...")
            if not db_manager.initialize():
                raise RuntimeError("Failed to initialize database connection")
        
        try: 
            with db_manager.get_session() as session: 
                task = ScrapingTask(
                    batch_id=self.batch_id,
                    task_type=task_type,
                    status="running",
                    started_at=datetime.now(), 
                )
                session.add(task)
                session.commit()
                self.logger.debug(f"📝 Created task: {task_type} ID: {task.id}")
                return task.id
        except Exception as e: 
            self.logger.error(f"❌ Failed to create task: {e}")
            return None 
    
    def update_task_status(self, 
                           task_id: int, 
                           status: str, 
                           success_count: int, 
                           fail_count: int,
                           error_message: str,
                           duration: int):
        if not task_id: 
            return 
        
        try: 
            with db_manager.get_session() as session: 
                task = session.query(ScrapingTask).filter_by(id=task_id).first()
                if task: 
                    task.status = status
                    task.success_count = success_count
                    task.fail_count = fail_count
                    task.error_message = error_message
                    task.duration = duration
                    session.commit()
                    self.logger.debug(f"📝 Updated task {task_id} status to: {status}")
        
        except Exception as e: 
            self.logger.error(f"❌ Failed to update task status: {e}")
     
     
    async def _save_validated_urls(self, validated_urls: List[ValidatedURL]) -> List[ValidatedURL]:
        """검증된 URL들을 데이터베이스에 저장"""
        start_time = time.time()
        
        try:
            self.logger.info(f"💾 Saving {len(validated_urls)} validated URLs to database...")
            
            with db_manager.get_session() as session:
                # URL들을 ScrapedUrl 테이블에 저장
                saved_count = 0
                for validated_url in validated_urls:
                    try:
                        scraped_url = ScrapedUrl(
                            batch_id=self.batch_id,
                            url=validated_url.job_url.full_url,
                            url_hash=hashlib.sha256(validated_url.job_url.full_url.encode()).hexdigest(),
                            status="success" if validated_url.is_valid else "failed",
                            error_message=validated_url.error_message if not validated_url.is_valid else None,
                            scraped_at=validated_url.validated_at
                        )
                        
                        session.add(scraped_url)
                        saved_count += 1
                        self.update_metrics(processed=1)
                    except IntegrityError:
                        session.rollback()
                        self.logger.warning(f"⚠️ URL already exists: {validated_url.job_url.full_url}")
                        self.update_metrics(failed=1)
                    except Exception as e:
                        session.rollback()
                        self.logger.error(f"❌ Failed to save URL {validated_url.job_url.full_url}: {e}")
                        self.update_metrics(failed=1)
                
                session.commit()
                
                # 통계 업데이트
                execution_time = int(time.time() - start_time)
                self.logger.info(f"✅ Saved {saved_count}/{len(validated_urls)} URLs to database in {execution_time:.2f}s")
                
        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")
            raise
        
        return validated_urls
    
    async def _save_job_details(self, job_details_list: List[JobDetails]) -> List[JobDetails]:
        """채용공고 상세정보들을 데이터베이스에 저장"""
        start_time = time.time()
        
        try:
            # 성공한 스크래핑 결과만 필터링
            successful_details = [jd for jd in job_details_list if jd.success]
            
            if not successful_details:
                self.logger.warning("📋 No successful job details to save")
                return job_details_list
            
            self.logger.info(f"💾 Saving {len(successful_details)} job details to database...")
            
            # 각 job_posting을 개별 트랜잭션으로 처리하여 롤백 문제 방지
            saved_count = 0
            for job_details in successful_details:
                try:
                    with db_manager.get_session() as session:
                        # 중복 확인 먼저 수행
                        existing_job = session.query(JobPosting).filter_by(
                            posting_id=job_details.job_url.posting_id
                        ).first()
                        
                        if existing_job:
                            self.logger.info(f"⏭️ Skipped duplicate job posting: {job_details.job_url.posting_id}")
                            self.update_metrics(processed=1)
                            continue
                        
                        # 회사 정보 저장 또는 조회
                        company = self._get_or_create_company(session, job_details)
                        
                        # 직무 카테고리 저장 또는 조회
                        job_category = self._get_or_create_job_category(session, job_details)
                        
                        # 위치 정보 저장 또는 조회
                        location = self._get_or_create_location(session, job_details)
                        
                        # 채용공고 저장
                        # 마감일 처리
                        deadline_text = job_details.job_description.get("deadline", "")
                        deadline_date, is_always_recruiting = self.deadline_parser.parse_deadline(deadline_text)
                        
                        job_posting = JobPosting(
                            posting_id=job_details.job_url.posting_id,
                            original_url=job_details.job_url.full_url,
                            job_category_id=job_category.job_category_id,
                            company_id=company.company_id,
                            location_id=location.location_id,
                            experience=job_details.job_description.get("experience", ""),
                            preferred=job_details.job_description.get("preferred", ""),
                            benefits=job_details.job_description.get("benefits",""),
                            hiring_process=job_details.job_description.get("hiring_process",""),
                            position=job_details.job_description.get("title",""),# job_details.job_url.position,
                            position_detail=job_details.job_description.get("position_detail", ""),
                            main_tasks=job_details.job_description.get("main_tasks", ""),
                            requirements=job_details.job_description.get("requirements", ""),
                            tags=job_details.job_description.get("tags", {}),
                            deadline=deadline_date,
                            is_always_recruiting=is_always_recruiting,
                            posted_date=job_details.posted_date
                        )
                        
                        session.add(job_posting)
                        session.commit()
                        saved_count += 1
                        self.update_metrics(processed=1)
                        
                except IntegrityError as e:
                    self.logger.warning(f"⚠️ Integrity error for job posting {job_details.job_url.posting_id}: {e}")
                    self.update_metrics(failed=1)
                except Exception as e:
                    self.logger.error(f"❌ Failed to save job details {job_details.job_url.full_url}: {e}")
                    self.update_metrics(failed=1)
                
            # 통계 업데이트
            execution_time = time.time() - start_time
            self.logger.info(f"✅ Saved {saved_count}/{len(successful_details)} job details to database in {execution_time:.2f}s")
                
        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")
            raise
        
        return job_details_list
    
    def _get_or_create_company(self, session: Session, job_details: JobDetails) -> Company:
        """회사 정보 조회 또는 생성"""
        company = session.query(Company).filter_by(company_name=job_details.job_url.company).first()
        
        if not company:
            company = Company(
                company_name=job_details.job_url.company,
                company_size=None,
                is_listed=None,
                blind_registered=None
            )
            session.add(company)
            session.commit()
        
        return company
    
    def _get_or_create_job_category(self, session: Session, job_details: JobDetails) -> JobCategory:
        """직무 카테고리 조회 또는 생성"""
        # 정규화된 job_specialty 값 추출
        job_specialty = None
        if hasattr(job_details, 'job_specialty') and job_details.job_specialty:
            job_specialty = job_details.job_specialty
        elif isinstance(job_details, dict) and 'job_specialty' in job_details:
            job_specialty = job_details['job_specialty']
        
        job_category = session.query(JobCategory).filter_by(
            job_category=job_details.job_url.job_category,
            job_field=job_details.job_field,
            scraper_type="wanted"
        ).first()
        
        if not job_category:
            job_category = JobCategory(
                job_category=job_details.job_url.job_category,
                job_field=job_details.job_field,
                job_specialty=job_specialty,  # 정규화된 직무명 저장
                scraper_type="wanted"
            )
            session.add(job_category)
            session.commit()
        else:
            # 기존 카테고리가 있어도 job_specialty가 비어있고 새로운 값이 있으면 업데이트
            if not job_category.job_specialty and job_specialty:
                job_category.job_specialty = job_specialty
                session.commit()
        
        return job_category
    
    def _get_or_create_location(self, session: Session, job_details: JobDetails) -> Location:
        """위치 정보 조회 또는 생성"""
        location_name = job_details.location or "미상"
        location_detail_name = job_details.location_detail
        
        location = session.query(Location).filter_by(
            location=location_name, 
            location_detail=location_detail_name
        ).first()
        
        if not location:
            location = Location(
                location=location_name,
                location_detail=location_detail_name
            )
            session.add(location)
            session.commit()
        
        return location
    
    async def execute(self, data) -> StageResult:
        """Stage 실행 (오버라이드)"""
        # 데이터베이스 연결 확인
        if not db_manager._initialized:
            self.logger.info("🔌 Initializing database connection...")
            if not db_manager.initialize():
                raise RuntimeError("Failed to initialize database connection")
        
        # 연결 테스트
        if not db_manager.test_connection():
            raise RuntimeError("Database connection test failed")
        
        # 부모 클래스의 execute 호출
        return await super().execute(data)