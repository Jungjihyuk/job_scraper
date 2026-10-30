# main_pipeline.py
import argparse
import sys
import time
import asyncio
from pathlib import Path

import inquirer

from app.core.logging import create_development_logger
from app.pipeline.data_models import PipelineConfig
from app.pipeline.manager import PipelineManager

logger = create_development_logger(__name__)

# 직무 선택 UI
questions = [
    inquirer.Checkbox(
        "job",
        message="🎯 Pipeline으로 수집할 직무를 선택하세요 (스페이스바로 체크 후 엔터):",
        choices=[
            "파이썬 개발자",
            "머신러닝 엔지니어",
            "데이터 엔지니어", 
            "서버 개발자",
            "데이터 사이언티스트",
            "빅데이터 엔지니어",
            ".NET 개발자",
        ],
    )
]

def get_job_selection():
    """직무 선택 처리"""
    # 환경변수에서 먼저 확인
    import os
    selected_job = os.environ.get("SELECTED_JOB")
    if selected_job:
        logger.info(f"🌐 웹에서 선택된 직무: {selected_job}")
        return selected_job
    
    # 환경변수가 없으면 CLI에서 선택
    answers = inquirer.prompt(questions)
    if answers is None or not answers["job"]:
        logger.error("❌ 직무를 선택하지 않았습니다.")
        sys.exit(1)
    return answers["job"][0]  # 첫 번째 선택된 직무만 사용

        
async def main(opt):
    """🚀 메인 실행 함수"""
    # 수집 모드 결정
    if opt.incremental:
        scrape_mode = "incremental"
    elif opt.full:
        scrape_mode = "full"
    else:
        scrape_mode = "default"

    logger.info("🚀 Starting Pipeline URL Collection + Validation Test...")
    config = PipelineConfig(
        job=opt.job,
        scraper_type="wanted",
        max_scrolls=opt.max_scrolls,
        scroll_delay=opt.scroll_delay,
        batch_size=10,
        request_timeout=10,
        enable_duplicate_check=True,
        scrape_mode=scrape_mode,
        # 저장 설정
        save_to_database=True,
        save_to_local=True,
        local_output_format="json",
        local_output_path="logs/"
    )
    MODE_LABELS = {"default": f"Default (max {config.max_scrolls} scrolls)",
                   "incremental": "Incremental (조기 종료)",
                   "full": "Full (페이지 끝까지)"}
    logger.info(f"⚙️ Pipeline Config:")
    logger.info(f"   🎯 Job: {config.job}")
    logger.info(f"   📦 Mode: {MODE_LABELS[scrape_mode]}")
    logger.info(f"   ⏱️ Scroll Delay: {config.scroll_delay}ms")

    # PipelineManager 사용
    pipeline_manager = PipelineManager(config)
    
    # 파이프라인 실행 (기본 저장 방식 사용)
    metrics = await pipeline_manager.run()
    
    logger.info(f"🎉 전체 파이프라인 완료! 총 {metrics.valid_urls + metrics.invalid_urls}건의 URL을 검증했습니다.")
    return metrics.valid_urls > 0 or metrics.invalid_urls > 0


def parse_opt(known=False):
    """🔧 명령행 인자 파싱"""
    parser = argparse.ArgumentParser(description="Pipeline URL Collection Test")
    
    # 직무는 인터랙티브하게 선택
    selected_job = get_job_selection()
    
    parser.add_argument(
        "--job", 
        type=str, 
        default=selected_job,
        help="Target job category"
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=100,  # 테스트용으로 줄임
        help="Maximum number of scrolls (default: 5)"
    )
    parser.add_argument(
        "--scroll-delay",
        type=int,
        default=2000,
        help="Delay between scrolls in milliseconds (default: 2000)"
    )
    # 수집 모드 (상호 배타)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental mode: 신규 공고가 거의 없으면 조기 종료"
    )
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Full mode: 페이지 끝까지 스크롤 (max-scrolls 무시)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_known_args()[0] if known else parser.parse_args()


if __name__ == "__main__":
    start_time = time.time()
    
    # 명령행 인자 파싱
    opt = parse_opt()
    
    # 디버그 모드 설정
    if opt.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Debug mode enabled")
    
    logger.info("🎬 Pipeline URL Collection Test Started")
    logger.info(f"📋 Selected job: {opt.job}")
    
    try:
        # 비동기 메인 함수 실행
        success = asyncio.run(main(opt))
        
        total_time = time.time() - start_time
        
        if success:
            logger.info(f"🎉 Test completed successfully in {total_time:.2f} seconds")
        else:
            logger.error(f"❌ Test failed after {total_time:.2f} seconds")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"❌ Unexpected error after {total_time:.2f} seconds: {e}", exc_info=True)
        sys.exit(1)