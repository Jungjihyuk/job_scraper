"""
대시보드 관련 Pydantic 스키마
"""

from typing import List
from pydantic import BaseModel
from .common import CompanySchema, ScrapingBatchSchema


class DashboardStatsResponse(BaseModel):
    """대시보드 통계 응답 스키마"""
    total_jobs: int
    total_companies: int
    recent_batches: int


class CompaniesResponse(BaseModel):
    """회사 목록 응답 스키마"""
    companies: List[CompanySchema]