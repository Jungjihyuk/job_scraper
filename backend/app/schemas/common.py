"""
공통 Pydantic 스키마
"""

from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel


class JobPostingSchema(BaseModel):
    """채용공고 스키마"""
    id: Optional[int] = None
    position: Optional[str] = None
    job_specialty: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    job_category: Optional[str] = None
    experience: Optional[str] = None
    deadline: Optional[str] = None  # ISO 날짜 형식 또는 None
    is_always_recruiting: Optional[bool] = None  # 상시채용 여부
    original_url: Optional[str] = None  # 원본 채용공고 URL
    posted_date: Optional[str] = None
    tags: Optional[Any] = None
    benefits: Optional[Any] = None
    domain: Optional[str] = None
    core_technologies: Optional[list] = None


class CompanySchema(BaseModel):
    """회사 스키마"""
    company_id: int
    company_name: str
    company_size: Optional[str] = None
    is_listed: Optional[bool] = None
    job_count: Optional[int] = None


class ScrapingBatchSchema(BaseModel):
    """스크래핑 배치 스키마"""
    id: int
    batch_name: str
    status: str
    total_urls: Optional[int] = None
    created_at: Optional[str] = None