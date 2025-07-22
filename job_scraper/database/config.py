"""
PostgreSQL 데이터베이스 설정
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    """데이터베이스 연결 설정"""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "db_name")
        self.username = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "1234")
        self.ssl_mode = os.getenv("DB_SSL_MODE", "prefer")
        
        # 연결 풀 설정
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    @property
    def database_url(self) -> str:
        """SQLAlchemy용 데이터베이스 URL"""
        return (
            f"postgresql://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    @property
    def async_database_url(self) -> str:
        """비동기 SQLAlchemy용 데이터베이스 URL"""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    def get_connection_kwargs(self) -> dict:
        """연결 옵션 딕셔너리"""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": True,  # 연결 상태 확인
        }


# 전역 설정 인스턴스
db_config = DatabaseConfig()