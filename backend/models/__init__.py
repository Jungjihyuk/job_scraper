"""
ORM models package.

Re-exports all models so existing imports remain unchanged:
    from backend.models import Base, JobPosting, Company, ...
"""

from backend.models.base import Base
from backend.models.scraping import ScrapingBatch, ScrapingTask, ScrapedUrl
from backend.models.job import (
    Company,
    JobCategory,
    Location,
    ExperienceCategory,
    JobPosting,
)

__all__ = [
    "Base",
    "ScrapingBatch",
    "ScrapingTask",
    "ScrapedUrl",
    "Company",
    "JobCategory",
    "Location",
    "ExperienceCategory",
    "JobPosting",
]
