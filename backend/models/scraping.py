"""
Scraping domain models: batch tracking, task management, URL records.
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import Base


class ScrapingBatch(Base):
    __tablename__ = "scraping_batches"

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
    tasks = relationship(
        "ScrapingTask", back_populates="batch", cascade="all, delete-orphan"
    )
    scraped_urls = relationship(
        "ScrapedUrl", back_populates="batch", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_scraping_batches_status", "status"),
        Index("idx_scraping_batches_type", "scraper_type"),
    )


class ScrapingTask(Base):
    __tablename__ = "scraping_tasks"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("scraping_batches.id"), nullable=False)
    task_type = Column(
        String(50), nullable=False
    )  # url_collector/url_validator/content_scraper/db_saver/total
    status = Column(String(20), nullable=False)  # pending/running/completed/failed
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

    __table_args__ = (Index("idx_scraping_tasks_batch", "batch_id"),)


class ScrapedUrl(Base):
    __tablename__ = "scraped_urls"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("scraping_batches.id"), nullable=False)
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
        Index("idx_scraped_urls_batch", "batch_id"),
        Index("idx_scraped_urls_status", "status"),
        Index("idx_scraped_urls_hash", "url_hash"),
    )
