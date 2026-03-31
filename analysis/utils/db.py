"""
DB 연결 및 데이터 로딩 유틸리티
analysis/.env 또는 상위 프로젝트의 .env에서 DATABASE_URL을 읽어 사용
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# .env 로드 (analysis/.env → 프로젝트 루트 .env 순서)
_analysis_env = Path(__file__).parent.parent / ".env"
_root_env = Path(__file__).parent.parent.parent / ".env"

if _analysis_env.exists():
    load_dotenv(_analysis_env)
elif _root_env.exists():
    load_dotenv(_root_env)


def get_engine(database_url: str = None):
    """SQLAlchemy 엔진 생성"""
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL이 설정되지 않았습니다. "
            ".env 파일에 DATABASE_URL을 추가하세요."
        )
    return create_engine(url)


def get_session(database_url: str = None) -> Session:
    """SQLAlchemy 세션 생성"""
    engine = get_engine(database_url)
    return sessionmaker(bind=engine)()


def load_job_postings(
    columns: list[str] = None,
    where: str = None,
    limit: int = None,
    database_url: str = None,
) -> pd.DataFrame:
    """
    job_posting 테이블에서 데이터를 DataFrame으로 로드

    Args:
        columns: 가져올 컬럼 리스트 (None이면 전체)
        where: WHERE 조건 (예: "main_tasks IS NOT NULL")
        limit: 최대 행 수
        database_url: DB 연결 URL (None이면 환경변수 사용)

    Returns:
        pd.DataFrame
    """
    engine = get_engine(database_url)

    col_str = ", ".join(columns) if columns else "*"
    query = f"SELECT {col_str} FROM job_posting"

    if where:
        query += f" WHERE {where}"
    if limit:
        query += f" LIMIT {limit}"

    return pd.read_sql(text(query), engine)
