#!/usr/bin/env python3
"""
기존 데이터베이스의 채용공고에 domain, core_technologies 태그를 재정규화하는 스크립트
"""

import sys
from pathlib import Path

# job_scraper 모듈 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import db_manager, init_database
from app.models import JobPosting
from app.pipeline.normalizers.content import ContentAnalyzer
from app.core.logging import create_development_logger

logger = create_development_logger(__name__)


def normalize_existing_domain_technology_data():
    """기존 job_posting 테이블의 도메인/핵심기술 데이터를 정규화"""

    print("🚀 기존 도메인/핵심기술 데이터 정규화 시작...")

    # 데이터베이스 초기화
    init_database()

    if not db_manager.test_connection():
        print("❌ 데이터베이스 연결 실패")
        return False

    analyzer = ContentAnalyzer()
    success_count = 0
    total_count = 0
    skip_count = 0

    try:
        with db_manager.get_session() as session:
            # domain이 NULL이고 본문 데이터가 있는 레코드 조회
            job_postings = session.query(JobPosting).filter(
                JobPosting.domain.is_(None),
                (JobPosting.main_tasks.isnot(None)) | (JobPosting.requirements.isnot(None))
            ).all()

            total_count = len(job_postings)
            print(f"📊 정규화할 채용공고 수: {total_count}")

            if total_count == 0:
                print("ℹ️ 정규화할 데이터가 없습니다.")
                return True

            for job_posting in job_postings:
                try:
                    # 본문 텍스트 결합
                    parts = []
                    if job_posting.main_tasks:
                        parts.append(job_posting.main_tasks)
                    if job_posting.requirements:
                        parts.append(job_posting.requirements)
                    if job_posting.preferred:
                        parts.append(job_posting.preferred)

                    body_text = " ".join(parts)
                    if not body_text.strip():
                        skip_count += 1
                        continue

                    # ContentAnalyzer로 분석
                    result = analyzer.analyze(body_text)

                    # 결과 업데이트
                    if result.domain:
                        job_posting.domain = result.domain
                    if result.core_technologies:
                        job_posting.core_technologies = result.core_technologies

                    if result.domain or result.core_technologies:
                        success_count += 1
                        if success_count <= 5:
                            print(
                                f"✅ posting_id={job_posting.posting_id}: "
                                f"domain={result.domain}, techs={result.core_technologies}"
                            )
                    else:
                        skip_count += 1

                    # 100건 단위 커밋
                    if (success_count + skip_count) % 100 == 0:
                        session.commit()
                        processed = success_count + skip_count
                        print(f"💾 중간 저장: {processed}/{total_count} 처리 ({success_count} 성공)")

                except Exception as e:
                    logger.error(
                        f"❌ 항목 처리 실패 (posting_id: {job_posting.posting_id}): {e}"
                    )
                    continue

            # 최종 커밋
            session.commit()

            print(f"\n🎉 도메인/핵심기술 정규화 완료!")
            print(f"  📊 전체: {total_count}")
            print(f"  ✅ 성공: {success_count}")
            print(f"  ⏭️  건너뜀: {skip_count}")
            print(f"  ❌ 실패: {total_count - success_count - skip_count}")

            # 최종 통계
            domain_count = session.query(JobPosting).filter(
                JobPosting.domain.isnot(None)
            ).count()
            tech_count = session.query(JobPosting).filter(
                JobPosting.core_technologies.isnot(None)
            ).count()

            print(f"\n📈 최종 통계:")
            print(f"  🏷️  도메인이 설정된 채용공고: {domain_count}")
            print(f"  🔧 핵심기술이 설정된 채용공고: {tech_count}")

            return True

    except Exception as e:
        logger.error(f"❌ 도메인/핵심기술 정규화 실패: {e}")
        print(f"❌ 도메인/핵심기술 정규화 실패: {e}")
        return False


if __name__ == "__main__":
    success = normalize_existing_domain_technology_data()

    if success:
        print("\n🎊 모든 작업이 성공적으로 완료되었습니다!")
    else:
        print("\n💥 작업 실행 중 오류가 발생했습니다!")
        sys.exit(1)
