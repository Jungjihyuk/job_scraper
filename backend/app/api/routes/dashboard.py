import os 

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.database import get_db_session
from app.models import JobPosting, Company, ScrapingBatch
from app.schemas.dashboard import (
    DashboardStatsResponse,
    CompaniesResponse
)

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(db: Session = Depends(get_db_session)) -> DashboardStatsResponse:
    """대시보드 통계 데이터 조회"""
    try: 
        # 전체 채용공고 수
        total_jobs = db.query(JobPosting).count()
        
        # 회사 수
        total_companies = db.query(Company).count()
        
        # 최근 스크래핑 배치
        recent_batches = db.query(ScrapingBatch)\
                           .filter(ScrapingBatch.status == 'completed')\
                           .count()                    
                           
        return DashboardStatsResponse(
            total_jobs=total_jobs,
            total_companies=total_companies,
            recent_batches=recent_batches
        )
        
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies", response_model=CompaniesResponse)
async def get_companies(limit: int = 10, db: Session = Depends(get_db_session)) -> CompaniesResponse:
    """회사 목록 조회"""
    try:
        companies = db.query(Company).limit(limit).all()
        
        companies_data = [
            {
                "company_id": company.company_id,
                "company_name": company.company_name,
                "company_size": company.company_size,
                "is_listed": company.is_listed,
                "job_count": len(company.job_postings)
            }
            for company in companies
        ]
        
        return CompaniesResponse(companies=companies_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
