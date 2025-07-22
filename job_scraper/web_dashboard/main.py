from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os

from job_scraper.database.connection import get_db_session, init_database
from job_scraper.database.models import (
    JobPosting, Company, JobCategory, Location, 
    ScrapingBatch
)

app = FastAPI(title="Job Scraper Dashboard", version="1.0.0")

# Static files 마운트
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# 데이터베이스 초기화
init_database()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """대시보드 메인 페이지"""
    html_file = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    with open(html_file, 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db_session)):
    """통계 데이터 조회"""
    try:
        # 전체 채용공고 수
        total_jobs = db.query(JobPosting).count()
        
        # 회사 수
        total_companies = db.query(Company).count()
        
        # 최근 스크래핑 배치
        recent_batches = db.query(ScrapingBatch).order_by(ScrapingBatch.created_at.desc()).limit(5).all()
        
        return {
            "total_jobs": total_jobs,
            "total_companies": total_companies,
            "recent_batches": [
                {
                    "id": batch.id,
                    "batch_name": batch.batch_name,
                    "status": batch.status,
                    "total_urls": batch.total_urls,
                    "created_at": batch.created_at.isoformat() if batch.created_at else None
                }
                for batch in recent_batches
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
async def get_jobs(limit: int = 20, offset: int = 0, db: Session = Depends(get_db_session)):
    """채용공고 목록 조회"""
    try:
        jobs = db.query(JobPosting).join(Company).join(JobCategory).join(Location).offset(offset).limit(limit).all()
        
        return {
            "jobs": [
                {
                    "id": job.id,
                    "position": job.position,
                    "company_name": job.company.company_name,
                    "location": job.location.location,
                    "job_category": job.job_category.job_category,
                    "experience": job.experience,
                    "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                    "tags": job.tags
                }
                for job in jobs
            ],
            "total": db.query(JobPosting).count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companies")
async def get_companies(limit: int = 10, db: Session = Depends(get_db_session)):
    """회사 목록 조회"""
    try:
        companies = db.query(Company).limit(limit).all()
        
        return {
            "companies": [
                {
                    "company_id": company.company_id,
                    "company_name": company.company_name,
                    "company_size": company.company_size,
                    "is_listed": company.is_listed,
                    "job_count": len(company.job_postings)
                }
                for company in companies
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)