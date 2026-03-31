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
    Float,
    ForeignKey,
    DECIMAL,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False, unique=True)
    company_type = Column(String(50))  # SI/대기업IT/솔루션/IT서비스/웹에이전시/스타트업
    company_size = Column(String(50))
    company_type_labels = Column(JSONB)  # 버전별 분류 결과 {"v1.0": "SI"}
    ai_confidence = Column(Float)  # LLM 분류 신뢰도 (0.0~1.0)
    source_info = Column(JSONB)  # 정보 출처 {"llm": true, "web_search": false}
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
    updated_at = Column(
        TIMESTAMP,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    # Relationships
    job_postings = relationship("JobPosting", back_populates="company")

    __table_args__ = (
        Index("idx_companies_name", "company_name"),
        Index("idx_companies_type", "company_type"),
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
    region = Column(String(20))  # 시/도 단위 (서울, 경기, 인천 등)

    # Relationships
    job_postings = relationship("JobPosting", back_populates="location")

    __table_args__ = (
        UniqueConstraint(
            "location", "location_detail", name="unique_location_combination"
        ),
        Index("idx_locations_region", "region"),
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
    domain_l1 = Column(String(50))  # 산업 도메인 대분류 (IT, 금융, 제조/하드웨어 등)
    domain_l2 = Column(String(100))  # 산업 도메인 중분류 (AI/딥테크, 핀테크 등)
    domain_l3 = Column(String(200))  # 산업 도메인 소분류 (필요 시 메모)
    specialty_l1 = Column(String(50))  # 직무 대분류 (AI/ML, 백엔드, 데이터, 인프라, 기타)
    specialty_l2 = Column(String(100))  # 직무 소분류 (AI Agent/LLM, 웹 백엔드 Python 등)
    employment_type = Column(String(30))  # 고용형태 (정규직, 프리랜서, 인턴, 계약직)
    core_technologies = Column(JSONB)  # 핵심 기술 태그
    taxonomy_version = Column(String(20))  # 분류 기준 버전 (FR-057)
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
        Index("idx_job_posting_domain_l1", "domain_l1"),
        Index("idx_job_posting_domain_l2", "domain_l2"),
        Index("idx_job_posting_specialty_l1", "specialty_l1"),
        Index("idx_job_posting_specialty_l2", "specialty_l2"),
        Index("idx_job_posting_employment_type", "employment_type"),
        Index("idx_job_posting_taxonomy_version", "taxonomy_version"),
    )
