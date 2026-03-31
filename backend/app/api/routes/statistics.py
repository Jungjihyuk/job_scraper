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
async def get_specialty_by_location(region: str = None, db: Session = Depends(get_db_session)):
    """
    지역별 직무 분포 데이터를 반환합니다.
    - region 미지정: 시/도 단위 요약
    - region 지정 (예: "서울"): 해당 시/도 내 구/시 단위 상세
    """
    try:
        # 드릴다운 여부에 따라 그룹핑 기준 결정
        if region:
            # 특정 시/도 내부: location(구/시) 단위로 집계
            location_col = Location.location
            base_filter = [Location.region == region]
        else:
            # 전국: region(시/도) 단위로 집계
            location_col = Location.region
            base_filter = [Location.region.is_not(None)]

        # 1단계: 지역별 상위 5개 직무를 찾아서 표시할 직무 목록 결정
        ranked = (
            db.query(
                location_col.label("loc"),
                JobPosting.specialty_l2,
                func.count(JobPosting.id).label("job_count"),
                func.row_number()
                .over(
                    partition_by=location_col,
                    order_by=func.count(JobPosting.id).desc(),
                )
                .label("rank"),
            )
            .join(JobPosting, Location.location_id == JobPosting.location_id)
            .filter(JobPosting.specialty_l2.is_not(None), *base_filter)
            .group_by(location_col, JobPosting.specialty_l2)
            .subquery()
        )

        top5_results = db.query(
            ranked.c.specialty_l2,
        ).filter(ranked.c.rank <= 5).distinct().all()

        if not top5_results:
            return {"labels": [], "datasets": [], "drilldown": region is None}

        top_specialties = sorted(set(r.specialty_l2 for r in top5_results))

        # 2단계: 해당 직무들의 실제 건수를 전체 지역에서 조회
        all_counts = (
            db.query(
                location_col.label("loc"),
                JobPosting.specialty_l2,
                func.count(JobPosting.id).label("job_count"),
            )
            .join(JobPosting, Location.location_id == JobPosting.location_id)
            .filter(JobPosting.specialty_l2.in_(top_specialties), *base_filter)
            .group_by(location_col, JobPosting.specialty_l2)
            .all()
        )

        # 데이터 가공
        locations = sorted(set(r.loc for r in all_counts))
        specialties = top_specialties

        specialty_colors = {
            spec: f"rgba({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)}, 0.7)"
            for spec in specialties
        }

        datasets = []
        for specialty in specialties:
            data = []
            for loc in locations:
                count = next((r.job_count for r in all_counts if r.loc == loc and r.specialty_l2 == specialty), 0)
                data.append(count)

            datasets.append({
                "label": specialty,
                "data": data,
                "backgroundColor": specialty_colors[specialty]
            })

        return {
            "labels": locations,
            "datasets": datasets,
            "drilldown": region is None,
            "current_region": region,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experience_by_specialty")
async def get_experience_by_specialty(db: Session = Depends(get_db_session)):
    """
    직무별 경력 분포 데이터를 반환합니다.
    min_years 기준 구직자 관점 구간: 신입가능, 1~3년, 3~5년, 5~10년, 10년+
    """
    try:
        from sqlalchemy import case, literal

        # min_years 기준 구간 라벨 매핑 (SQL CASE)
        exp_bucket = case(
            (ExperienceCategory.is_fresh_welcome == True, literal("신입 가능")),
            (ExperienceCategory.min_years == None, literal("미상")),
            (ExperienceCategory.min_years == 0, literal("신입 가능")),
            (ExperienceCategory.min_years <= 2, literal("1~2년 이상")),
            (ExperienceCategory.min_years <= 4, literal("3~4년 이상")),
            (ExperienceCategory.min_years <= 6, literal("5~6년 이상")),
            (ExperienceCategory.min_years <= 9, literal("7~9년 이상")),
            else_=literal("10년 이상"),
        ).label("exp_bucket")

        results = (
            db.query(
                JobPosting.specialty_l2,
                exp_bucket,
                func.count(JobPosting.id).label("job_count"),
            )
            .outerjoin(ExperienceCategory, JobPosting.experience_category_id == ExperienceCategory.experience_category_id)
            .filter(JobPosting.specialty_l2.is_not(None))
            .group_by(JobPosting.specialty_l2, exp_bucket)
            .all()
        )

        if not results:
            return {"labels": [], "datasets": []}

        # 데이터 가공
        specialties = sorted(set(r.specialty_l2 for r in results))

        # 순서 고정
        bucket_order = ["신입 가능", "1~2년 이상", "3~4년 이상", "5~6년 이상", "7~9년 이상", "10년 이상", "미상"]
        experiences = [b for b in bucket_order if any(r.exp_bucket == b for r in results)]

        experience_colors = {
            "신입 가능": "rgba(16, 185, 129, 0.7)",
            "1~2년 이상": "rgba(99, 102, 241, 0.7)",
            "3~4년 이상": "rgba(245, 158, 11, 0.7)",
            "5~6년 이상": "rgba(249, 115, 22, 0.7)",
            "7~9년 이상": "rgba(239, 68, 68, 0.7)",
            "10년 이상": "rgba(139, 92, 246, 0.7)",
            "미상": "rgba(148, 163, 184, 0.7)",
        }

        datasets = []
        for experience in experiences:
            data = []
            for specialty in specialties:
                count = next((r.job_count for r in results if r.specialty_l2 == specialty and r.exp_bucket == experience), 0)
                data.append(count)

            datasets.append({
                "label": experience,
                "data": data,
                "backgroundColor": experience_colors.get(experience, "rgba(148, 163, 184, 0.7)")
            })

        return {"labels": specialties, "datasets": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/posting_trends")
async def get_posting_trends(specialty: str = None, year: int = None, db: Session = Depends(get_db_session)):
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

        if specialty:
            query = query.filter(JobPosting.specialty_l2 == specialty)

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
            "label": specialty if specialty else "전체",
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

# 카테고리성 태그 제외 목록 (기술 스택이 아닌 분야/개념명)
EXCLUDED_TECH_TAGS = {
    "딥러닝", "머신러닝", "컴퓨터비전", "NLP", "Computer Vision",
    "Cloud/Infra", "Data Engineering", "데이터엔지니어링", "Search",
    "시계열", "이상탐지", "강화학습", "생성형 AI", "로보틱스",
}

@router.get("/technology_by_company_type")
async def get_technology_by_company_type(
    top_n: int = 10,
    db: Session = Depends(get_db_session),
):
    """
    기업 유형별 기술 스택 분포 (개별 레이더 차트용).
    각 기업유형별 자체 상위 N개 기술을 비율(%)로 반환.
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

        # {company_type: {tech: count}}
        ct_tech_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        ct_posting_counts: dict[str, int] = defaultdict(int)

        for row in rows:
            techs = row.core_technologies
            if not isinstance(techs, list):
                continue
            ct_posting_counts[row.company_type] += 1
            for t in techs:
                tech_name = t if isinstance(t, str) else str(t)
                if tech_name in EXCLUDED_TECH_TAGS:
                    continue
                ct_tech_counts[row.company_type][tech_name] += 1

        if not ct_tech_counts:
            return {"charts": []}

        # 미분류를 맨 뒤로
        company_types = sorted(ct_tech_counts.keys(), key=lambda x: (x == '미분류', x))

        charts = []
        for i, ct in enumerate(company_types):
            total = ct_posting_counts.get(ct, 1)
            tech_counts = ct_tech_counts[ct]
            top_techs = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

            data = [
                {"subject": tech, "value": round(cnt / total * 100, 1)}
                for tech, cnt in top_techs
            ]

            charts.append({
                "company_type": ct,
                "posting_count": total,
                "color": COLORS[i % len(COLORS)],
                "data": data,
            })

        return {"charts": charts}

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
