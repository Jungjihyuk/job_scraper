"""
채용공고 관련 Pydantic 스키마
"""

from typing import List, Optional
from pydantic import BaseModel
from .common import JobPostingSchema


class JobListResponse(BaseModel):
    """채용공고 목록 응답 스키마"""
    jobs: List[JobPostingSchema]
    total: Optional[int] = None


class JobCategoriesResponse(BaseModel):
    """직무 카테고리 응답 스키마"""
    categories: List[str]


class ExperiencesResponse(BaseModel):
    """경력 목록 응답 스키마"""
    experiences: List[str]


class LocationsResponse(BaseModel):
    """지역 목록 응답 스키마"""
    locations: List[str]


class DomainsResponse(BaseModel):
    """도메인 목록 응답 스키마"""
    domains: List[str]


class TechnologiesResponse(BaseModel):
    """기술 목록 응답 스키마"""
    technologies: List[str]


class JobFilterRequest(BaseModel):
    """채용공고 필터 요청 스키마"""
    position: Optional[str] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    limit: int = 10