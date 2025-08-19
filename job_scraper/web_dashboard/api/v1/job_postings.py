"""
채용 공고 내용과 관련된 모든 기능 
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from job_scraper.database.connection import get_db_session
from job_scraper.database.models import JobPosting, JobCategory, Location, Company, ExperienceCategory
from job_scraper.web_dashboard.schemas.job_postings import (
    JobListResponse,
    JobCategoriesResponse,
    ExperiencesResponse,
    LocationsResponse,
    JobFilterRequest
)

router = APIRouter(prefix='/api/job_postings', tags=['job_postings'])

@router.get('/deadline', response_model=JobListResponse)
async def get_job_postings(
    job_specialty: str = None,
    experience: str = None,
    location: str = None,
    include_always_recruiting: bool = True,
    include_expired: bool = False,
    limit: int = 10,  
    db: Session = Depends(get_db_session)
) -> JobListResponse: 
    """마감일 임박 채용 공고 가져오기 (마감된 공고 제외 가능)"""
    try: 
        
        # JOIN 테이블 생성 (ExperienceCategory 포함)
        query = db.query(JobPosting).join(JobCategory)\
                                    .join(Company)\
                                    .join(Location)\
                                    .outerjoin(ExperienceCategory)
        
        # 조건 검색을 위한 필터
        if job_specialty:
            query = query.filter(JobCategory.job_specialty == job_specialty)    
        if experience: 
            query = query.filter(ExperienceCategory.standardized_experience == experience)
        if location: 
            query = query.filter(Location.location == location)
        
        # 상시채용 포함 여부 필터링
        if not include_always_recruiting:
            query = query.filter(JobPosting.is_always_recruiting == False)
        
        # 마감된 공고 제외 (기본값: 제외)
        if not include_expired:
            from datetime import date
            today = date.today()
            # 마감일이 없거나(상시채용) 오늘 이후인 것만 포함
            query = query.filter(
                (JobPosting.deadline.is_(None)) | (JobPosting.deadline >= today)
            )
        
        # 개선된 정렬: 실제 마감일이 있는 것 우선, 그 다음 상시채용
        # NULLS LAST를 사용하여 NULL 값(상시채용)을 마지막에 배치
        from sqlalchemy import nullslast
        job_postings = query.order_by(nullslast(JobPosting.deadline)).limit(limit).all()

        jobs = [
            {
                "position": job_posting.position,
                "job_specialty": job_posting.job_category.job_specialty,
                "company_name": job_posting.company.company_name,
                "location": job_posting.location.location,
                "experience": job_posting.experience_category.standardized_experience if job_posting.experience_category else job_posting.experience,
                "deadline": job_posting.deadline.isoformat() if job_posting.deadline else None,
                "is_always_recruiting": job_posting.is_always_recruiting,
                "original_url": job_posting.original_url,
                "tags": job_posting.tags
            }
            for job_posting in job_postings
        ]
        
        return JobListResponse(jobs=jobs)
    
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/recent', response_model=JobListResponse)
async def get_recent_job_postings(
    limit: int = 10,
    exclude_always_recruiting: bool = False,
    db: Session = Depends(get_db_session)
) -> JobListResponse:
    """최근 등록된 채용 공고 가져오기"""
    try:
        from sqlalchemy import desc
        
        query = db.query(JobPosting).join(JobCategory)\
                                    .join(Company)\
                                    .join(Location)\
                                    .outerjoin(ExperienceCategory)
        
        # 상시채용 제외 필터링
        if exclude_always_recruiting:
            query = query.filter(JobPosting.is_always_recruiting == False)
        
        job_postings = query.order_by(desc(JobPosting.posted_date)).limit(limit).all()

        jobs = [
            {
                "position": job_posting.position,
                "job_specialty": job_posting.job_category.job_specialty,
                "company_name": job_posting.company.company_name,
                "location": job_posting.location.location,
                "experience": job_posting.experience_category.standardized_experience if job_posting.experience_category else job_posting.experience,
                "deadline": job_posting.deadline.isoformat() if job_posting.deadline else None,
                "is_always_recruiting": job_posting.is_always_recruiting,
                "original_url": job_posting.original_url,
                "tags": job_posting.tags,
                "posted_date": job_posting.posted_date.isoformat() if job_posting.posted_date else None
            }
            for job_posting in job_postings
        ]
        
        return JobListResponse(jobs=jobs)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/job', response_model=JobCategoriesResponse)
async def get_job_categories(db: Session = Depends(get_db_session)) -> JobCategoriesResponse:
    """모든 표준 직무 조회 (job_specialty 기반)"""
    
    try: 
        job_specialties = db.query(JobCategory.job_specialty)\
                           .distinct()\
                           .filter(JobCategory.job_specialty.is_not(None))\
                           .all()
        
        categories = [specialty[0] for specialty in job_specialties]
        return JobCategoriesResponse(categories=categories)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/experience', response_model=ExperiencesResponse)
async def get_experience(db: Session = Depends(get_db_session)) -> ExperiencesResponse:
    """모든 정규화된 경력 조회"""
    
    try: 
        experiences = db.query(ExperienceCategory.standardized_experience)\
                           .distinct()\
                           .filter(ExperienceCategory.standardized_experience.is_not(None))\
                           .order_by(ExperienceCategory.standardized_experience)\
                           .all()
        
        exp_list = [experience[0] for experience in experiences]
        return ExperiencesResponse(experiences=exp_list)
        
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/location', response_model=LocationsResponse)
async def get_location(db: Session = Depends(get_db_session)) -> LocationsResponse:
    """모든 위치 조회"""
    
    try: 
        locations = db.query(Location.location)\
                           .distinct()\
                           .filter(Location.location.is_not(None))\
                           .all()
        
        location_list = [location[0] for location in locations]
        return LocationsResponse(locations=location_list)
        
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e)) 