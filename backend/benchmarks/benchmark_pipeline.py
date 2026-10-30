"""파이프라인 성능 벤치마크 스크립트.

cProfile과 tracemalloc을 사용하여 파이프라인의 CPU 시간과 메모리 사용량을 측정한다.

실행 방법:
    cd backend
    uv run benchmarks/benchmark_pipeline.py                    # 기본 실행 (CPU 프로파일링)
    uv run benchmarks/benchmark_pipeline.py --mode memory      # 메모리 프로파일링
    uv run benchmarks/benchmark_pipeline.py --mode both        # 둘 다

결과 확인:
    # cProfile 결과를 snakeviz로 시각화
    snakeviz benchmarks/profiles/pipeline.prof

    # 메모리 결과는 터미널에 Top 10 출력 + reports/ 에 텍스트 저장

TODO:
    - [ ] 실행해보고 결과 .prof 파일이 profiles/ 에 생성되는지 확인
    - [ ] snakeviz로 열어서 어떤 함수가 가장 오래 걸리는지 확인
    - [ ] tracemalloc 결과에서 어떤 스테이지가 메모리를 많이 쓰는지 확인
    - [ ] 필요하면 line_profiler로 특정 함수를 줄 단위로 분석
"""

import argparse
import asyncio
import cProfile
import pstats
import tracemalloc
from datetime import datetime

from conftest import PROFILES_DIR, REPORTS_DIR, create_config
from app.pipeline.manager import PipelineManager


async def run_pipeline(config):
    """파이프라인을 실행하고 결과를 반환한다."""
    manager = PipelineManager(config)
    metrics = await manager.run()
    return metrics


def profile_cpu(config):
    """cProfile로 CPU 시간을 측정한다.

    생성 파일: benchmarks/profiles/pipeline_{timestamp}.prof

    TODO: 결과 파일을 snakeviz로 열어보자.
        snakeviz benchmarks/profiles/pipeline_XXXXXX.prof
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prof_path = PROFILES_DIR / f"pipeline_{timestamp}.prof"

    profiler = cProfile.Profile()
    profiler.enable()

    asyncio.run(run_pipeline(config))

    profiler.disable()
    profiler.dump_stats(str(prof_path))

    # 터미널에 상위 20개 함수 요약 출력
    stats = pstats.Stats(str(prof_path))
    stats.sort_stats("cumulative")
    print("\n" + "=" * 60)
    print("CPU 프로파일링 결과 (상위 20개 함수)")
    print("=" * 60)
    stats.print_stats(20)
    print(f"\n.prof 파일 저장: {prof_path}")
    print(f"시각화: snakeviz {prof_path}")


def profile_memory(config):
    """tracemalloc으로 메모리 사용량을 측정한다.

    파이프라인 실행 전후 스냅샷을 비교하여 메모리 증가량 Top 10을 출력한다.

    TODO: 출력 결과에서 어떤 파일의 어떤 라인이 메모리를 많이 쓰는지 확인해보자.
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    asyncio.run(run_pipeline(config))

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # 스냅샷 비교: 실행 전후 메모리 증가량 Top 10
    stats = snapshot_after.compare_to(snapshot_before, "lineno")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"memory_{timestamp}.txt"

    lines = []
    lines.append("=" * 60)
    lines.append("메모리 프로파일링 결과 (증가량 Top 10)")
    lines.append("=" * 60)
    for stat in stats[:10]:
        lines.append(str(stat))

    report_text = "\n".join(lines)
    print("\n" + report_text)

    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n리포트 저장: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="파이프라인 성능 벤치마크")
    parser.add_argument(
        "--mode",
        choices=["cpu", "memory", "both"],
        default="cpu",
        help="프로파일링 모드 (기본: cpu)",
    )
    parser.add_argument(
        "--job",
        default="백엔드 개발자",
        help="스크래핑 대상 직무 (기본: 백엔드 개발자)",
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=2,
        help="최대 스크롤 횟수 (기본: 2)",
    )
    args = parser.parse_args()

    config = create_config(job=args.job, max_scrolls=args.max_scrolls)
    print(f"벤치마크 설정: job={config.job}, max_scrolls={config.max_scrolls}, mode={args.mode}")

    if args.mode in ("cpu", "both"):
        profile_cpu(config)

    if args.mode in ("memory", "both"):
        profile_memory(config)


if __name__ == "__main__":
    main()
