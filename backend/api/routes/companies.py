"""
회사 정보와 관련된 API 기능
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.core.database import get_db_session
from backend.models import Company

router = APIRouter(prefix='/api/companies', tags=['companies'])

@router.get("")
async def get_companies(db: Session = Depends(get_db_session)):
    """
    등록된 모든 회사 목록을 반환합니다.
    """
    try:
        companies = db.query(Company).options(joinedload(Company.job_postings)).order_by(Company.company_name).all()
        
        company_list = [
            {
                "company_name": company.company_name,
                "company_size": company.company_size,
                "is_listed": company.is_listed,
                "job_count": len(company.job_postings)
            }
            for company in companies
        ]
        
        return {"companies": company_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
