"""
Database models for job scraper application based on PostgreSQL schema.
"""
from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, Boolean, 
    ForeignKey, DECIMAL, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ScrapingBatch(Base):
    __tablename__ = 'scraping_batches'
    
    id = Column(Integer, primary_key=True)
    batch_name = Column(String(255), nullable=False)
    scraper_type = Column(String(50), nullable=False)  # wanted/saramin/jobkorea
    status = Column(String(20), nullable=False)  # pending/running/completed/failed
    total_urls = Column(Integer)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    tasks = relationship("ScrapingTask", back_populates="batch", cascade="all, delete-orphan")
    scraped_urls = relationship("ScrapedUrl", back_populates="batch", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_scraping_batches_status', 'status'),
        Index('idx_scraping_batches_type', 'scraper_type'),
    )


class ScrapingTask(Base):
    __tablename__ = 'scraping_tasks'
    
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('scraping_batches.id'), nullable=False)
    task_type = Column(String(50), nullable=False)  # url_collector/url_validator/content_scraper/db_saver/total
    status = Column(String(20), nullable=False)  # pending/running/completed/failed
    url_count = Column(Integer)
    success_count = Column(Integer)
    fail_count = Column(Integer)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer)
    started_at = Column(TIMESTAMP)
    duration = Column(Integer)  # seconds
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    batch = relationship("ScrapingBatch", back_populates="tasks")
    
    __table_args__ = (
        Index('idx_scraping_tasks_batch', 'batch_id'),
    )


class ScrapedUrl(Base):
    __tablename__ = 'scraped_urls'
    
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('scraping_batches.id'), nullable=False)
    url = Column(String(2048), nullable=False)
    url_hash = Column(String(64), unique=True, nullable=False)
    status = Column(String(20), nullable=False)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    scraped_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    batch = relationship("ScrapingBatch", back_populates="scraped_urls")
    
    __table_args__ = (
        Index('idx_scraped_urls_batch', 'batch_id'),
        Index('idx_scraped_urls_status', 'status'),
        Index('idx_scraped_urls_hash', 'url_hash'),
    )


class Company(Base):
    __tablename__ = 'companies'
    
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
        Index('idx_companies_name', 'company_name'),
        Index('idx_companies_listing', 'is_listed', 'listing_market'),
    )


class JobCategory(Base):
    __tablename__ = 'job_categories'
    
    job_category_id = Column(Integer, primary_key=True)
    job_category = Column(String(100), nullable=False)
    job_field = Column(String(100), nullable=False)
    job_specialty = Column(String(100))
    scraper_type = Column(String(50), nullable=False)  # wanted/saramin/jobkorea
    
    # Relationships
    job_postings = relationship("JobPosting", back_populates="job_category")
    
    __table_args__ = (
        UniqueConstraint('job_category', 'job_field', 'job_specialty', name='unique_job_combination'),
    )


class Location(Base):
    __tablename__ = 'locations'
    
    location_id = Column(Integer, primary_key=True)
    location = Column(String(100), nullable=False)
    location_detail = Column(String(255))
    
    # Relationships
    job_postings = relationship("JobPosting", back_populates="location")

    __table_args__ = (
        UniqueConstraint('location', 'location_detail', name='unique_location_combination'),
    )


class JobPosting(Base):
    __tablename__ = 'job_posting'
    
    id = Column(Integer, primary_key=True)
    posting_id = Column(String(100), unique=True, nullable=False)
    job_category_id = Column(Integer, ForeignKey('job_categories.job_category_id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.company_id'), nullable=False)
    location_id = Column(Integer, ForeignKey('locations.location_id'), nullable=False)
    experience = Column(String(50))
    position = Column(String(255))
    position_detail = Column(Text)
    main_tasks = Column(Text)
    requirements = Column(Text)
    preferred = Column(Text)
    benefits = Column(Text)
    tags = Column(JSON)
    hiring_process = Column(Text)
    deadline = Column(String(50))
    posted_date = Column(TIMESTAMP)
    
    # Relationships
    company = relationship("Company", back_populates="job_postings")
    job_category = relationship("JobCategory", back_populates="job_postings")
    location = relationship("Location", back_populates="job_postings")
    
    __table_args__ = (
        Index('idx_job_posting_company', 'company_id'),
        Index('idx_job_posting_location', 'location_id'),
        Index('idx_job_posting_category', 'job_category_id'),
        Index('idx_job_posting_posted_date', 'posted_date'),
    )