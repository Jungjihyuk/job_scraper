"""
통계 데이터와 관련된 모든 기능
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, extract
import random

from app.core.database import get_db_session
from app.models import JobPosting, JobCategory, Location, ExperienceCategory, Company
from sqlalchemy.dialects.postgresql import JSONB

router = APIRouter(prefix='/api/statistics', tags=['statistics'])

COLORS = [
    'rgba(99, 102, 241, 0.7)',   # indigo
    'rgba(245, 158, 11, 0.7)',   # amber
    'rgba(16, 185, 129, 0.7)',   # emerald
    'rgba(239, 68, 68, 0.7)',    # red
    'rgba(139, 92, 246, 0.7)',   # violet
    'rgba(6, 182, 212, 0.7)',    # cyan
    'rgba(249, 115, 22, 0.7)',   # orange
    'rgba(20, 184, 166, 0.7)',   # teal
    'rgba(236, 72, 153, 0.7)',   # pink
    'rgba(132, 204, 22, 0.7)',   # lime
]

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

@router.get("/domain_distribution")
async def get_domain_distribution(db: Session = Depends(get_db_session)):
    """
    도메인별 채용공고 수 분포를 반환합니다.
    """
    try:
        results = (
            db.query(
                JobPosting.domain_l2,
                func.count(JobPosting.id).label("job_count"),
            )
            .filter(JobPosting.domain_l2.is_not(None))
            .group_by(JobPosting.domain_l2)
            .order_by(func.count(JobPosting.id).desc())
            .all()
        )

        if not results:
            return {"labels": [], "datasets": []}

        labels = [r.domain_l2 for r in results]
        data = [r.job_count for r in results]

        dataset = {
            "label": "공고 수",
            "data": data,
            "backgroundColor": [
                f"rgba({(i * 47 + 100) % 256}, {(i * 83 + 50) % 256}, {(i * 131 + 150) % 256}, 0.7)"
                for i in range(len(labels))
            ],
        }

        return {"labels": labels, "datasets": [dataset]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technology_trends")
async def get_technology_trends(
    technology: str = None,
    year: int = None,
    db: Session = Depends(get_db_session),
):
    """
    기술별 월간 트렌드를 반환합니다. ORM 쿼리 후 Python에서 JSONB 배열을 풀어냅니다.
    """
    try:
        from collections import defaultdict

        query = (
            db.query(
                JobPosting.posted_date,
                JobPosting.core_technologies,
            )
            .filter(
                JobPosting.posted_date.is_not(None),
                JobPosting.core_technologies.is_not(None),
            )
        )

        if year:
            query = query.filter(extract('year', JobPosting.posted_date) == year)

        rows = query.all()

        # Python에서 JSONB 배열 unnest + 월별 집계
        # {(month, tech): count}
        counts = defaultdict(int)
        for row in rows:
            techs = row.core_technologies
            if not isinstance(techs, list):
                continue
            month = row.posted_date.strftime('%Y-%m')
            for t in techs:
                tech_name = t if isinstance(t, str) else str(t)
                if technology and tech_name != technology:
                    continue
                counts[(month, tech_name)] += 1

        if not counts:
            return {"labels": [], "datasets": []}

        months = sorted(set(m for m, _ in counts))
        technologies_set = sorted(set(t for _, t in counts))

        datasets = []
        for i, tech in enumerate(technologies_set):
            data = [counts.get((m, tech), 0) for m in months]
            datasets.append({
                "label": tech,
                "data": data,
                "borderColor": f"rgba({(i * 47 + 100) % 256}, {(i * 83 + 50) % 256}, {(i * 131 + 150) % 256}, 1)",
                "backgroundColor": f"rgba({(i * 47 + 100) % 256}, {(i * 83 + 50) % 256}, {(i * 131 + 150) % 256}, 0.2)",
                "fill": False,
                "tension": 0.1,
            })

        return {"labels": months, "datasets": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company_type_distribution")
async def get_company_type_distribution(db: Session = Depends(get_db_session)):
    """
    기업 유형별 채용공고 수 분포를 반환합니다.
    """
    try:
        results = (
            db.query(
                Company.company_type,
                func.count(JobPosting.id).label("job_count"),
            )
            .join(JobPosting, Company.company_id == JobPosting.company_id)
            .filter(Company.company_type.is_not(None))
            .group_by(Company.company_type)
            .order_by(func.count(JobPosting.id).desc())
            .all()
        )

        if not results:
            return {"labels": [], "datasets": []}

        labels = [r.company_type for r in results]
        data = [r.job_count for r in results]

        dataset = {
            "label": "공고 수",
            "data": data,
            "backgroundColor": [
                COLORS[i % len(COLORS)] for i in range(len(labels))
            ],
        }

        return {"labels": labels, "datasets": [dataset]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/domain_by_company_type")
async def get_domain_by_company_type(db: Session = Depends(get_db_session)):
    """
    기업 유형별 도메인 분포 (stacked bar).
    X축: 기업유형, 각 bar segment: 도메인
    """
    try:
        results = (
            db.query(
                Company.company_type,
                JobPosting.domain_l2,
                func.count(JobPosting.id).label("job_count"),
            )
            .join(JobPosting, Company.company_id == JobPosting.company_id)
            .filter(
                Company.company_type.is_not(None),
                JobPosting.domain_l2.is_not(None),
            )
            .group_by(Company.company_type, JobPosting.domain_l2)
            .all()
        )

        if not results:
            return {"labels": [], "datasets": []}

        company_types = sorted(set(r.company_type for r in results))
        domains = sorted(set(r.domain_l2 for r in results))

        datasets = []
        for i, domain in enumerate(domains):
            data = []
            for ct in company_types:
                count = next(
                    (r.job_count for r in results
                     if r.company_type == ct and r.domain_l2 == domain),
                    0,
                )
                data.append(count)
            datasets.append({
                "label": domain,
                "data": data,
                "backgroundColor": COLORS[i % len(COLORS)],
            })

        return {"labels": company_types, "datasets": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technology_by_company_type")
async def get_technology_by_company_type(
    top_n: int = 10,
    db: Session = Depends(get_db_session),
):
    """
    기업 유형별 기술 스택 분포 (stacked bar).
    상위 N개 기술만 표시.
    """
    try:
        from collections import defaultdict

        rows = (
            db.query(
                Company.company_type,
                JobPosting.core_technologies,
            )
            .join(JobPosting, Company.company_id == JobPosting.company_id)
            .filter(
                Company.company_type.is_not(None),
                JobPosting.core_technologies.is_not(None),
            )
            .all()
        )

        # {(company_type, tech): count}
        counts: dict[tuple[str, str], int] = defaultdict(int)
        tech_totals: dict[str, int] = defaultdict(int)
        for row in rows:
            techs = row.core_technologies
            if not isinstance(techs, list):
                continue
            for t in techs:
                tech_name = t if isinstance(t, str) else str(t)
                counts[(row.company_type, tech_name)] += 1
                tech_totals[tech_name] += 1

        if not counts:
            return {"labels": [], "datasets": []}

        # 상위 N개 기술만
        top_techs = sorted(tech_totals, key=tech_totals.get, reverse=True)[:top_n]
        company_types = sorted(set(ct for ct, _ in counts))

        datasets = []
        for i, tech in enumerate(top_techs):
            data = [counts.get((ct, tech), 0) for ct in company_types]
            datasets.append({
                "label": tech,
                "data": data,
                "backgroundColor": COLORS[i % len(COLORS)],
            })

        return {"labels": company_types, "datasets": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available_technologies")
async def get_available_technologies(db: Session = Depends(get_db_session)):
    """
    사용 가능한 핵심 기술 목록을 반환합니다.
    """
    try:
        rows = (
            db.query(JobPosting.core_technologies)
            .filter(JobPosting.core_technologies.is_not(None))
            .all()
        )

        tech_set = set()
        for row in rows:
            techs = row.core_technologies
            if not isinstance(techs, list):
                continue
            for t in techs:
                tech_set.add(t if isinstance(t, str) else str(t))

        return {"technologies": sorted(tech_set)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
