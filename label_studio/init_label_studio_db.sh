#!/bin/bash
# =============================================================================
# PostgreSQL 컨테이너 초기화 스크립트 (docker-entrypoint-initdb.d)
#
# docker-compose.yml에서 postgres 볼륨으로 마운트되어 컨테이너 최초 기동 시
# 자동 실행됩니다. Label Studio 전용 DB(label_studio_db)를 생성합니다.
# 이미 존재하면 건너뜁니다.
# =============================================================================
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE label_studio_db OWNER $POSTGRES_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'label_studio_db')\gexec
EOSQL
