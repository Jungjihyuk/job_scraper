"""
ORM models package.

Re-exports all models so existing imports remain unchanged:
    from app.models import Base, JobPosting, Company, ...
"""

from app.models.base import Base
from app.models.scraping import ScrapingBatch, ScrapingTask, ScrapedUrl
from app.models.job import (
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
