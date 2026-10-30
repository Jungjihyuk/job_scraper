"""벤치마크 공통 설정.

이 파일은 벤치마크 실행에 필요한 공통 설정과 유틸리티를 제공한다.

사용법:
    from conftest import PROFILES_DIR, REPORTS_DIR, create_config
"""

import sys
from pathlib import Path

# backend/ 를 sys.path에 추가하여 app 패키지 import 가능하게 함
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 벤치마크 결과 저장 경로
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"

from app.pipeline.data_models import PipelineConfig


def create_config(
    job: str = "백엔드 개발자",
    max_scrolls: int = 2,
) -> PipelineConfig:
    """DB/파일 저장 없이 네트워크만 타는 벤치마크용 PipelineConfig 생성.

    TODO: 필요에 따라 파라미터를 추가하거나 기본값을 조정해보자.
        - batch_size: 배치 크기를 바꿔가며 최적값 탐색
        - scroll_delay: 스크롤 딜레이를 조절하며 속도/안정성 트레이드오프 확인
        - scrape_mode: "default", "incremental", "full" 모드별 성능 비교
    """
    return PipelineConfig(
        job=job,
        max_scrolls=max_scrolls,
        save_to_database=False,
        save_to_local=False,
    )
