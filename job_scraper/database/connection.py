"""
PostgreSQL 데이터베이스 연결 관리
"""
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from job_scraper.database.config import db_config
from job_scraper.database.models import Base
from job_scraper.config.logging_config import create_development_logger

logger = create_development_logger(__name__)


class DatabaseManager:
    """데이터베이스 연결 및 세션 관리"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """데이터베이스 연결 초기화"""
        try:
            logger.info("🔌 Initializing database connection...")
            
            # SQLAlchemy 엔진 생성
            self.engine = create_engine(
                db_config.database_url,
                **db_config.get_connection_kwargs(),
                echo=False  # SQL 로깅 (개발시에는 True)
            )
            
            # 세션 팩토리 생성
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # 연결 테스트
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._initialized = True
            logger.info(f"✅ Database connection initialized: {db_config.host}:{db_config.port}/{db_config.database}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            return False
    
    def create_tables(self) -> bool:
        """데이터베이스 테이블 생성"""
        try:
            if not self._initialized:
                raise RuntimeError("Database not initialized")
            
            logger.info("🏗️ Creating database tables...")
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    def drop_tables(self) -> bool:
        """데이터베이스 테이블 삭제 (주의!)"""
        try:
            if not self._initialized:
                raise RuntimeError("Database not initialized")
            
            logger.warning("⚠️ Dropping all database tables...")
            Base.metadata.drop_all(bind=self.engine)
            logger.info("✅ Database tables dropped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to drop tables: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """데이터베이스 세션 컨텍스트 매니저"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """직접 세션 반환 (수동 관리 필요)"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.engine:
            self.engine.dispose()
            logger.info("🔒 Database connection closed")
            self._initialized = False


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


# 편의 함수들
def get_db_session() -> Generator[Session, None, None]:
    """데이터베이스 세션 획득 (FastAPI 의존성 주입용)"""
    with db_manager.get_session() as session:
        yield session


def init_database() -> bool:
    """데이터베이스 초기화"""
    success = db_manager.initialize()
    if success:
        db_manager.create_tables()
    return success


def test_database_connection() -> bool:
    """데이터베이스 연결 테스트"""
    return db_manager.test_connection()