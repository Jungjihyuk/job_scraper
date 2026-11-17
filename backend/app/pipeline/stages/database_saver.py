"""
데이터베이스 저장 Stage
스크래핑된 데이터를 PostgreSQL에 저장
"""

import math
import time
import hashlib
from typing import List, Union, Optional
from uuid import uuid4
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.pipeline.stages.base import BaseStage
from app.pipeline.data_models import (
    JobPostingData,
    ValidatedURL,
    JobDetails,
    JobSaveResult,
    StageResult,
)
from app.core.database import db_manager
from app.models import (
    ScrapingBatch,
    ScrapingTask,
    ScrapedUrl,
    JobPosting,
    Company,
    JobCategory,
    Location,
    ExperienceCategory,
)
from app.utils.deadline_parser import DeadlineParser


def url_hash(url: str) -> str:
    """scraped_urls.url_hash에 쓰는 해시를 만든다.

    Args:
        url: 공고 주소.

    Returns:
        주소의 SHA-256 16진수 문자열.
    """
    return hashlib.sha256(url.encode()).hexdigest()


class DatabaseSaverStage(BaseStage):
    """데이터베이스 저장 Stage"""

    def __init__(self):
        super().__init__("DatabaseSaver")
        self.deadline_parser = DeadlineParser()
        self.batch_id = None
        self.session_id = str(uuid4())[:8]

    async def process(
        self, data: Union[List[JobPostingData], List[ValidatedURL], List[JobDetails]]
    ):  # -> Union[List[ValidatedURL], List[JobDetails]]:
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
                    total_urls=None,
                    started_at=datetime.now(),
                )
                session.add(batch)
                session.commit()
                self.batch_id = batch.id
                self.logger.info(
                    f"📝 Created main batch: {batch_name} ID: {self.batch_id}"
                )
                return self.batch_id

        except Exception as e:
            self.logger.error(f"❌ Failed to create main batch: {e}")
            raise

    def _cleanup_incomplete_batches(self, session: Session, scraper_type: str):
        """이전 실행의 미완료 배치들을 failed로 업데이트"""
        try:
            incomplete_batches = (
                session.query(ScrapingBatch)
                .filter_by(status="running", scraper_type=scraper_type)
                .all()
            )

            if incomplete_batches:
                for batch in incomplete_batches:
                    batch.status = "failed"
                    batch.completed_at = datetime.now()

                session.commit()
                self.logger.info(
                    f"🧹 Cleaned up {len(incomplete_batches)} incomplete batches"
                )

        except Exception as e:
            self.logger.warning(f"⚠️ Failed to cleanup incomplete batches: {e}")
            # 정리 실패해도 새 배치 생성은 계속 진행

    def update_batch_status(
        self,
        status: str,
        total_urls: int,
        collected: int = 0,
        saved: int = 0,
        failed: int = 0,
        skipped: int = 0,
    ) -> None:
        """배치 상태와 실행 결과 건수를 쓴다.

        Args:
            status: 배치 상태.
            total_urls: 검증한 URL 수.
            collected: 목록에서 수집한 공고 수.
            saved: 저장한 공고 수.
            failed: 상세 추출과 저장에 실패한 공고 수.
            skipped: 3회 제한으로 건너뛴 공고 수.
        """
        if not self.batch_id:
            return

        try:
            with db_manager.get_session() as session:
                batch = session.query(ScrapingBatch).filter_by(id=self.batch_id).first()
                if batch:
                    batch.status = status
                    batch.total_urls = total_urls
                    batch.collected_count = collected
                    batch.saved_count = saved
                    batch.failed_count = failed
                    batch.skipped_count = skipped

                    if status in ["completed", "partial", "failed"]:
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

    def update_task_status(
        self,
        task_id: int,
        status: str,
        success_count: int,
        fail_count: int,
        error_message: str,
        duration: float,
    ):
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
                    # 정수 초 열이라 올림해 1초 미만이 0으로 남지 않게 한다
                    task.duration = math.ceil(duration)
                    session.commit()
                    self.logger.debug(f"📝 Updated task {task_id} status to: {status}")

        except Exception as e:
            self.logger.error(f"❌ Failed to update task status: {e}")

    async def _save_validated_urls(
        self, validated_urls: List[ValidatedURL]
    ) -> List[ValidatedURL]:
        """검증된 URL들을 저장한다. 이미 있는 URL은 건드리지 않고 건너뛴다."""
        start_time = time.time()

        try:
            self.logger.info(
                f"💾 Saving {len(validated_urls)} validated URLs to database..."
            )

            rows = [
                {
                    "batch_id": self.batch_id,
                    "url": validated_url.job_url.full_url,
                    "url_hash": url_hash(validated_url.job_url.full_url),
                    "status": "success" if validated_url.is_valid else "failed",
                    "error_message": validated_url.error_message
                    if not validated_url.is_valid
                    else None,
                    "scraped_at": validated_url.validated_at,
                }
                for validated_url in validated_urls
            ]
            statement = (
                insert(ScrapedUrl)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["url_hash"])
                .returning(ScrapedUrl.id)
            )

            with db_manager.get_session() as session:
                # 드라이버의 rowcount는 -1일 수 있어 실제 삽입된 행을 센다
                saved_count = len(session.execute(statement).all())
                session.commit()

            self.update_metrics(processed=saved_count)
            self.logger.info(
                f"✅ Saved {saved_count}/{len(validated_urls)} URLs to database "
                f"({len(validated_urls) - saved_count} already existed) "
                f"in {time.time() - start_time:.2f}s"
            )

        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")
            raise

        return validated_urls

    async def _save_job_details(
        self, job_details_list: List[JobDetails]
    ) -> JobSaveResult:
        """상세 추출에 성공한 공고를 저장하고 공고별 결과를 돌려준다."""
        start_time = time.time()
        result = JobSaveResult()

        try:
            # 성공한 스크래핑 결과만 필터링
            successful_details = [jd for jd in job_details_list if jd.success]

            if not successful_details:
                self.logger.warning("📋 No successful job details to save")
                return result

            self.logger.info(
                f"💾 Saving {len(successful_details)} job details to database..."
            )

            # 각 job_posting을 개별 트랜잭션으로 처리하여 롤백 문제 방지
            for job_details in successful_details:
                try:
                    with db_manager.get_session() as session:
                        # 중복 확인 먼저 수행
                        existing_job = (
                            session.query(JobPosting)
                            .filter_by(posting_id=job_details.job_url.posting_id)
                            .first()
                        )

                        if existing_job:
                            self.logger.info(
                                f"⏭️ Skipped duplicate job posting: {job_details.job_url.posting_id}"
                            )
                            result.duplicates += 1
                            continue

                        # 회사 정보 저장 또는 조회
                        company = self._get_or_create_company(session, job_details)

                        # 직무 카테고리 저장 또는 조회
                        job_category = self._get_or_create_job_category(
                            session, job_details
                        )

                        # 위치 정보 저장 또는 조회
                        location = self._get_or_create_location(session, job_details)

                        experience_category = self._get_or_create_experience_category(
                            session, job_details
                        )

                        # 마감일 처리
                        deadline_text = job_details.job_description.get("deadline", "")
                        deadline_date, is_always_recruiting = (
                            self.deadline_parser.parse_deadline(deadline_text)
                        )

                        job_posting = JobPosting(
                            posting_id=job_details.job_url.posting_id,
                            original_url=job_details.job_url.full_url,
                            job_category_id=job_category.job_category_id,
                            company_id=company.company_id,
                            location_id=location.location_id,
                            experience_category_id=(
                                experience_category.experience_category_id
                                if experience_category
                                else None
                            ),
                            experience=job_details.job_description.get("experience"),
                            preferred=job_details.job_description.get("preferred"),
                            benefits=job_details.job_description.get("benefits"),
                            hiring_process=job_details.job_description.get(
                                "hiring_process"
                            ),
                            position=job_details.job_description.get(
                                "title"
                            ),  # job_details.job_url.position,
                            position_detail=job_details.job_description.get(
                                "position_detail"
                            ),
                            main_tasks=job_details.job_description.get("main_tasks"),
                            requirements=job_details.job_description.get(
                                "requirements"
                            ),
                            tags=job_details.job_description.get("tags", []),
                            deadline=deadline_date,
                            is_always_recruiting=is_always_recruiting,
                            domain_l2=job_details.job_description.get("domain"),
                            specialty_l1=job_details.job_description.get("specialty_l1"),
                            specialty_l2=job_details.job_description.get("specialty_l2"),
                            employment_type=job_details.job_description.get("employment_type"),
                            core_technologies=job_details.job_description.get("core_technologies"),
                            posted_date=job_details.posted_date,
                            normalization_failed=job_details.normalization_failed,
                        )

                        session.add(job_posting)
                        # 다시 수집해 성공한 공고는 실패 기록을 지운다
                        session.query(ScrapedUrl).filter_by(
                            url_hash=url_hash(job_details.job_url.full_url)
                        ).update(
                            {
                                "status": "success",
                                "retry_count": 0,
                                "error_message": None,
                            },
                            synchronize_session=False,
                        )
                        session.commit()
                        result.saved.append(job_details)
                        self.update_metrics(processed=1)

                except IntegrityError as e:
                    self.logger.warning(
                        f"⚠️ Integrity error for job posting {job_details.job_url.posting_id}: {e}"
                    )
                    job_details.error_message = f"DB 저장 실패: {e}"
                    result.failed.append(job_details)
                    self.update_metrics(failed=1)
                except Exception as e:
                    self.logger.error(
                        f"❌ Failed to save job details {job_details.job_url.full_url}: {e}"
                    )
                    job_details.error_message = f"DB 저장 실패: {e}"
                    result.failed.append(job_details)
                    self.update_metrics(failed=1)

            # 통계 업데이트
            execution_time = time.time() - start_time
            self.logger.info(
                f"✅ Saved {len(result.saved)}/{len(successful_details)} job details "
                f"({len(result.failed)} failed, {result.duplicates} duplicates) "
                f"in {execution_time:.2f}s"
            )

        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")
            raise

        return result

    def record_failures(self, failed_details: List[JobDetails]) -> None:
        """실패한 공고의 실패 횟수와 원인을 scraped_urls에 남긴다.

        상세 추출 실패와 저장 실패를 모두 센다. 기록에 실패해도 실행은 계속한다.

        Args:
            failed_details: 실패한 공고. `error_message`에 원인이 있다.
        """
        if not failed_details:
            return

        try:
            with db_manager.get_session() as session:
                for details in failed_details:
                    session.query(ScrapedUrl).filter_by(
                        url_hash=url_hash(details.job_url.full_url)
                    ).update(
                        {
                            "status": "failed",
                            "retry_count": func.coalesce(ScrapedUrl.retry_count, 0)
                            + 1,
                            "error_message": details.error_message,
                        },
                        synchronize_session=False,
                    )
                session.commit()
        except Exception as e:
            self.logger.error(f"❌ Failed to record failures: {e}")

    def _get_or_create_company(
        self, session: Session, job_details: JobDetails
    ) -> Company:
        """회사 정보 조회 또는 생성"""
        company = (
            session.query(Company)
            .filter_by(company_name=job_details.job_url.company)
            .first()
        )

        if not company:
            company = Company(
                company_name=job_details.job_url.company,
                company_size=None,
                is_listed=None,
                blind_registered=None,
            )
            session.add(company)
            session.commit()

        return company

    def _get_or_create_job_category(
        self, session: Session, job_details: JobDetails
    ) -> JobCategory:
        """직무 카테고리 조회 또는 생성"""
        # 정규화된 job_specialty 값 추출 (JobNormalizerStage가 job_description에 저장)
        job_specialty = None
        if job_details.job_description:
            job_specialty = job_details.job_description.get("job_specialty")

        job_category = (
            session.query(JobCategory)
            .filter_by(
                job_category=job_details.job_url.job_category,
                job_field=job_details.job_field,
                scraper_type="wanted",
            )
            .first()
        )

        if not job_category:
            job_category = JobCategory(
                job_category=job_details.job_url.job_category,
                job_field=job_details.job_field,
                job_specialty=job_specialty,  # 정규화된 직무명 저장
                scraper_type="wanted",
            )
            session.add(job_category)
            session.commit()
        else:
            # 기존 카테고리가 있어도 job_specialty가 비어있고 새로운 값이 있으면 업데이트
            if not job_category.job_specialty and job_specialty:
                job_category.job_specialty = job_specialty
                session.commit()

        return job_category

    def _get_or_create_experience_category(
        self, session: Session, job_details: JobDetails
    ) -> Optional[ExperienceCategory]:
        if not job_details.job_description:
            return None

        norm_data = job_details.job_description.get("experience_normalization")
        if not norm_data:
            return None

        raw_experience = norm_data.get("raw_experience")
        if not raw_experience:
            return None

        experience_category = (
            session.query(ExperienceCategory)
            .filter_by(raw_experience=raw_experience)
            .first()
        )

        if not experience_category:
            experience_category = ExperienceCategory(
                raw_experience=raw_experience,
                standardized_experience=norm_data.get("standardized_experience"),
                min_years=norm_data.get("min_years"),
                max_years=norm_data.get("max_years"),
                is_fresh_welcome=norm_data.get("is_fresh_welcome", False),
                confidence=norm_data.get("confidence"),
                matching_method=norm_data.get("matching_method"),
                manual_review=norm_data.get("manual_review", False),
            )
            session.add(experience_category)
            session.flush()
            self.logger.debug(
                f"📝 Created ExperienceCategory: '{raw_experience}' "
                f"→ '{norm_data.get('standardized_experience')}'"
            )
        else:
            new_confidence = norm_data.get("confidence")
            if new_confidence and (
                experience_category.confidence is None
                or float(new_confidence) > float(experience_category.confidence)
            ):
                experience_category.standardized_experience = norm_data.get(
                    "standardized_experience"
                )
                experience_category.min_years = norm_data.get("min_years")
                experience_category.max_years = norm_data.get("max_years")
                experience_category.is_fresh_welcome = norm_data.get(
                    "is_fresh_welcome", False
                )
                experience_category.confidence = new_confidence
                experience_category.matching_method = norm_data.get("matching_method")
                experience_category.manual_review = norm_data.get(
                    "manual_review", False
                )
                session.flush()

        return experience_category

    def _get_or_create_location(
        self, session: Session, job_details: JobDetails
    ) -> Location:
        """위치 정보 조회 또는 생성"""
        location_name = job_details.location or "미상"
        location_detail_name = job_details.location_detail

        location = (
            session.query(Location)
            .filter_by(location=location_name, location_detail=location_detail_name)
            .first()
        )

        if not location:
            region = location_name.split(" ", 1)[0] if location_name else None
            location = Location(
                location=location_name,
                location_detail=location_detail_name,
                region=region,
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
