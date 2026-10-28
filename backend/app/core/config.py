"""
PostgreSQL 데이터베이스 설정
"""
import logging
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """데이터베이스 연결 설정"""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "db_name")
        self.username = os.getenv("DB_USER", "postgres")
        _password = os.getenv("DB_PASSWORD")
        if _password is None:
            logger.warning("DB_PASSWORD 환경변수가 설정되지 않았습니다. 기본값을 사용합니다.")
        self.password = _password or "1234"
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

# Query parameter
JOB_CONFIG = {
    "job_id": {
        "파이썬 개발자": 899,
        "머신러닝 엔지니어": 1634,
        "데이터 엔지니어": 655,
        "서버 개발자": 872,
        "빅데이터 엔지니어": 1025,
        "데이터 사이언티스트": 1024,
        "프론트엔드 개발자": 669, 
        ".NET 개발자": 661,
    },
    "params": {
        "country": "kr",
        "job_sort": "job.recommend_order",
        "years": -1,
        "locations": "gyeonggi.all",
    },
}

# 공통 헤더 정보
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
}

# User-Agent 리스트
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]
