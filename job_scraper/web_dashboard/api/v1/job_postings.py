"""
채용 공고 내용과 관련된 모든 기능 
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from job_scraper.database.connection import get_db_session
from job_scraper.database.models import JobPosting, JobCategory, Location, Company
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
    position: str = None,
    experience: str = None,
    location: str = None,
    limit: int = 10,  
    db: Session = Depends(get_db_session)
) -> JobListResponse: 
    """마감일 임박 채용 공고 가져오기"""
    try: 
        
        # JOIN 테이블 생성 
        query = db.query(JobPosting).join(JobCategory)\
                                    .join(Company)\
                                    .join(Location)
        
        # 조건 검색을 위한 필터 
        if position:
            query = query.filter(JobPosting.position == position)    
        if experience: 
            query = query.filter(JobPosting.experience == experience)
        if location: 
            query = query.filter(Location.location == location)
        
        # 가장 날짜가 가까운 순으로 정렬 (오름차순)
        job_postings = query.order_by(JobPosting.deadline).limit(limit).all()

        jobs = [
            {
                "position": job_posting.position,
                "company_name": job_posting.company.company_name,
                "location": job_posting.location.location,
                "experience": job_posting.experience, 
                "tags": job_posting.tags
            }
            for job_posting in job_postings
        ]
        
        return JobListResponse(jobs=jobs)
    
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/job', response_model=JobCategoriesResponse)
async def get_job_categories(db: Session = Depends(get_db_session)) -> JobCategoriesResponse:
    """모든 직무 조회"""
    
    try: 
        job_categories = db.query(JobPosting.position)\
                           .distinct()\
                           .filter(JobPosting.position.is_not(None))\
                           .all()
        
        categories = [category[0] for category in job_categories]
        return JobCategoriesResponse(categories=categories)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/experience', response_model=ExperiencesResponse)
async def get_experience(db: Session = Depends(get_db_session)) -> ExperiencesResponse:
    """모든 경력 조회"""
    
    try: 
        experiences = db.query(JobPosting.experience)\
                           .distinct()\
                           .filter(JobPosting.experience.is_not(None))\
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