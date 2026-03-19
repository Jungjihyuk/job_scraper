"""
Job domain models: companies, categories, locations, postings.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    TIMESTAMP,
    Boolean,
    DATE,
    ForeignKey,
    DECIMAL,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import Base


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    company_size = Column(String(50))
    is_listed = Column(Boolean)
    listing_market = Column(String(20))  # KOSPI/KOSDAQ
    stock_code = Column(String(20))
    blind_registered = Column(Boolean)
    blind_avg_rating = Column(DECIMAL(2, 1))
    blind_career_rating = Column(DECIMAL(2, 1))
    blind_worklife_rating = Column(DECIMAL(2, 1))
    blind_welfare_rating = Column(DECIMAL(2, 1))
    blind_culture_rating = Column(DECIMAL(2, 1))
    blind_management_rating = Column(DECIMAL(2, 1))
    blind_last_updated = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

    # Relationships
    job_postings = relationship("JobPosting", back_populates="company")

    __table_args__ = (
        Index("idx_companies_name", "company_name"),
        Index("idx_companies_listing", "is_listed", "listing_market"),
    )


class JobCategory(Base):
    __tablename__ = "job_categories"

    job_category_id = Column(Integer, primary_key=True)
    job_category = Column(String(100), nullable=False)
    job_field = Column(String(100), nullable=False)
    job_specialty = Column(String(100))
    scraper_type = Column(String(50), nullable=False)  # wanted/saramin/jobkorea

    # Relationships
    job_postings = relationship("JobPosting", back_populates="job_category")

    __table_args__ = (
        UniqueConstraint(
            "job_category", "job_field", "job_specialty", name="unique_job_combination"
        ),
    )


class Location(Base):
    __tablename__ = "locations"

    location_id = Column(Integer, primary_key=True)
    location = Column(String(100), nullable=False)
    location_detail = Column(String(255))

    # Relationships
    job_postings = relationship("JobPosting", back_populates="location")

    __table_args__ = (
        UniqueConstraint(
            "location", "location_detail", name="unique_location_combination"
        ),
    )


class ExperienceCategory(Base):
    __tablename__ = "experience_categories"

    experience_category_id = Column(Integer, primary_key=True)
    raw_experience = Column(String(100), nullable=False, unique=True)
    standardized_experience = Column(String(50))
    min_years = Column(Integer)
    max_years = Column(Integer)
    is_fresh_welcome = Column(Boolean, default=False)
    confidence = Column(DECIMAL(3, 2))
    matching_method = Column(String(50))
    manual_review = Column(Boolean, default=False)
    correction = Column(String(50))
    review_note = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

    # Relationships
    job_postings = relationship("JobPosting", back_populates="experience_category")

    __table_args__ = (
        Index("idx_experience_standardized", "standardized_experience"),
        Index("idx_experience_years", "min_years", "max_years"),
        Index("idx_experience_fresh", "is_fresh_welcome"),
    )


class JobPosting(Base):
    __tablename__ = "job_posting"

    id = Column(Integer, primary_key=True)
    posting_id = Column(String(100), unique=True, nullable=False)
    original_url = Column(String(2048))  # 원본 채용공고 URL
    job_category_id = Column(
        Integer, ForeignKey("job_categories.job_category_id"), nullable=False
    )
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.location_id"), nullable=False)
    experience_category_id = Column(
        Integer,
        ForeignKey("experience_categories.experience_category_id"),
        nullable=True,
    )
    experience = Column(String(50))
    position = Column(String(255))
    position_detail = Column(Text)
    main_tasks = Column(Text)
    requirements = Column(Text)
    preferred = Column(Text)
    benefits = Column(Text)
    tags = Column(JSON)
    hiring_process = Column(Text)
    deadline = Column(DATE)  # 실제 마감일 (상시채용인 경우 NULL)
    is_always_recruiting = Column(Boolean, default=False)  # 상시채용 여부
    domain = Column(String(100))  # 산업 도메인
    core_technologies = Column(JSON)  # 핵심 기술 태그
    posted_date = Column(TIMESTAMP)

    # Relationships
    company = relationship("Company", back_populates="job_postings")
    job_category = relationship("JobCategory", back_populates="job_postings")
    location = relationship("Location", back_populates="job_postings")
    experience_category = relationship(
        "ExperienceCategory", back_populates="job_postings"
    )

    __table_args__ = (
        Index("idx_job_posting_company", "company_id"),
        Index("idx_job_posting_location", "location_id"),
        Index("idx_job_posting_category", "job_category_id"),
        Index("idx_job_posting_experience", "experience_category_id"),
        Index("idx_job_posting_posted_date", "posted_date"),
        Index("idx_job_posting_deadline", "deadline"),
        Index("idx_job_posting_always_recruiting", "is_always_recruiting"),
        Index("idx_job_posting_domain", "domain"),
    )
