"""
통계 데이터와 관련된 모든 기능
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, extract
import random

from job_scraper.database.connection import get_db_session
from job_scraper.database.models import JobPosting, JobCategory, Location, ExperienceCategory

router = APIRouter(prefix='/api/statistics', tags=['statistics'])

@router.get("/specialty_by_location")
async def get_specialty_by_location(db: Session = Depends(get_db_session)):
    """
    지역별 상위 5개 직무 분포 데이터를 반환합니다.
    """
    try:
        # 지역별, 직무별 공고 수 집계
        subquery = (
            db.query(
                Location.location,
                JobCategory.job_specialty,
                func.count(JobPosting.id).label("job_count"),
                func.row_number()
                .over(
                    partition_by=Location.location,
                    order_by=func.count(JobPosting.id).desc(),
                )
                .label("rank"),
            )
            .join(JobPosting, Location.location_id == JobPosting.location_id)
            .join(JobCategory, JobCategory.job_category_id == JobPosting.job_category_id)
            .filter(JobCategory.job_specialty.is_not(None))
            .group_by(Location.location, JobCategory.job_specialty)
            .subquery()
        )

        results = db.query(
            subquery.c.location,
            subquery.c.job_specialty,
            subquery.c.job_count
        ).filter(subquery.c.rank <= 5).all()

        if not results:
            return {"labels": [], "datasets": []}

        # 데이터 가공
        locations = sorted(list(set([r.location for r in results])))
        specialties = sorted(list(set([r.job_specialty for r in results])))
        
        # 직무별 색상 랜덤 매핑
        specialty_colors = {
            spec: f"rgba({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)}, 0.7)"
            for spec in specialties
        }

        datasets = []
        for specialty in specialties:
            data = []
            for location in locations:
                count = next((r.job_count for r in results if r.location == location and r.job_specialty == specialty), 0)
                data.append(count)
            
            datasets.append({
                "label": specialty,
                "data": data,
                "backgroundColor": specialty_colors[specialty]
            })

        return {"labels": locations, "datasets": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experience_by_specialty")
async def get_experience_by_specialty(db: Session = Depends(get_db_session)):
    """
    직무별 경력 분포 데이터를 반환합니다.
    """
    try:
        results = (
            db.query(
                JobCategory.job_specialty,
                ExperienceCategory.standardized_experience,
                func.count(JobPosting.id).label("job_count"),
            )
            .join(JobPosting, JobCategory.job_category_id == JobPosting.job_category_id)
            .outerjoin(ExperienceCategory, JobPosting.experience_category_id == ExperienceCategory.experience_category_id)
            .filter(JobCategory.job_specialty.is_not(None))
            .group_by(JobCategory.job_specialty, ExperienceCategory.standardized_experience)
            .order_by(JobCategory.job_specialty, ExperienceCategory.standardized_experience)
            .all()
        )

        if not results:
            return {"labels": [], "datasets": []}

        # 데이터 가공
        specialties = sorted(list(set([r.job_specialty for r in results])))
        
        # None을 '미지정'으로 대체하여 정렬 오류 방지
        experiences_list = [r.standardized_experience if r.standardized_experience is not None else '미지정' for r in results]
        experiences = sorted(list(set(experiences_list)))

        # 경력별 색상 랜덤 매핑
        experience_colors = {
            exp: f"rgba({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)}, 0.7)"
            for exp in experiences
        }

        datasets = []
        for experience in experiences:
            data = []
            for specialty in specialties:
                # '미지정'으로 바꾼 None 값을 다시 None으로 바꿔서 쿼리 결과와 매칭
                lookup_experience = experience if experience != '미지정' else None
                count = next((r.job_count for r in results if r.job_specialty == specialty and r.standardized_experience == lookup_experience), 0)
                data.append(count)
            
            datasets.append({
                "label": experience,
                "data": data,
                "backgroundColor": experience_colors[experience]
            })

        return {"labels": specialties, "datasets": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/posting_trends")
async def get_posting_trends(job_specialty: str = None, year: int = None, db: Session = Depends(get_db_session)):
    """
    시간에 따른 채용 공고 수 추이 데이터를 반환합니다.
    """
    try:
        query = (
            db.query(
                cast(JobPosting.posted_date, Date).label("post_day"),
                func.count(JobPosting.id).label("job_count"),
            )
            .filter(JobPosting.posted_date.is_not(None))
        )

        if job_specialty:
            query = query.join(JobCategory, JobPosting.job_category_id == JobCategory.job_category_id)                         .filter(JobCategory.job_specialty == job_specialty)
        
        if year:
            query = query.filter(extract('year', JobPosting.posted_date) == year)

        results = (
            query.group_by("post_day")
            .order_by("post_day")
            .all()
        )

        if not results:
            return {"labels": [], "datasets": []}

        labels = [r.post_day.isoformat() for r in results]
        data = [r.job_count for r in results]

        dataset = {
            "label": job_specialty if job_specialty else "전체",
            "data": data,
            "borderColor": f"rgba({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)}, 1)",
            "backgroundColor": f"rgba({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)}, 0.2)",
            "fill": True,
            "tension": 0.1
        }

        return {"labels": labels, "datasets": [dataset]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available_years")
async def get_available_years(db: Session = Depends(get_db_session)):
    """
    채용 공고 데이터가 있는 모든 연도를 반환합니다.
    """
    try:
        years = (
            db.query(extract('year', JobPosting.posted_date).label("year"))
            .filter(JobPosting.posted_date.is_not(None))
            .distinct()
            .order_by(extract('year', JobPosting.posted_date).desc())
            .all()
        )
        return {"years": [y.year for y in years]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
