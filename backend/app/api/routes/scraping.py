"""
스크래핑 작업에 관련된 기능
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
import subprocess
import asyncio
import json
from typing import Optional

from app.pipeline.data_models import PIPELINE_RESULT_PREFIX
from app.schemas.scraping import (
    ScrapingRequest,
    ScrapingResponse,
    ScrapingStatusResponse,
)

# 프로세스가 끝난 뒤 남은 출력을 기다리는 시간. 자식 프로세스가 파이프를 쥐고
# 있으면 출력이 끝나지 않으므로 제한을 둔다.
OUTPUT_DRAIN_TIMEOUT_SECONDS = 5
EXIT_POLL_INTERVAL_SECONDS = 0.2


router = APIRouter(prefix="/api/scraping", tags=["scraping"])


@router.post("/start", response_model=ScrapingResponse)
async def start_scraping(
    request: ScrapingRequest, background_tasks: BackgroundTasks
) -> ScrapingResponse:
    """스크래핑 파이프라인 시작"""
    try:
        # 백그라운드에서 파이프라인 실행
        background_tasks.add_task(
            run_pipeline, request.scraper_type, request.job, request.scrape_mode
        )

        mode_labels = {
            "default": "기본",
            "incremental": "증분 수집",
            "full": "전체 수집",
        }
        return ScrapingResponse(
            message=f"스크래핑이 시작되었습니다 ({mode_labels.get(request.scrape_mode, request.scrape_mode)})",
            scraper_type=request.scraper_type,
            job=request.job,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def wait_for_exit(process: asyncio.subprocess.Process) -> int:
    """파이프 상태와 상관없이 프로세스가 끝나기를 기다린다.

    `Process.wait()`는 파이프가 모두 닫힐 때까지 돌아오지 않아, 자식 프로세스가
    파이프를 쥐고 있으면 끝난 프로세스도 영원히 기다린다.

    Args:
        process: 기다릴 프로세스.

    Returns:
        종료 코드.
    """
    while process.returncode is None:
        await asyncio.sleep(EXIT_POLL_INTERVAL_SECONDS)
    return process.returncode


def parse_pipeline_result(line: str) -> dict | None:
    """stdout 한 줄이 실행 결과 줄이면 읽는다.

    Args:
        line: 앞뒤 공백을 지운 stdout 한 줄.

    Returns:
        실행 결과. 결과 줄이 아니거나 형식이 깨졌으면 None.
    """
    if not line.startswith(PIPELINE_RESULT_PREFIX):
        return None
    try:
        result = json.loads(line.removeprefix(PIPELINE_RESULT_PREFIX))
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None


def build_finish_event(job: str, returncode: int, result: dict | None) -> dict:
    """프로세스 종료를 알리는 WebSocket 이벤트를 만든다.

    Args:
        job: 수집한 직무.
        returncode: 프로세스 종료 코드.
        result: CLI가 남긴 실행 결과. 없으면 종료 코드로만 판단한다.

    Returns:
        `complete`나 `error` 이벤트.
    """
    event: dict = (
        {"type": "complete", "progress": 100}
        if returncode == 0
        else {
            "type": "error",
            "message": f"❌ 스크래핑 실패 (종료 코드: {returncode})",
        }
    )
    if returncode == 0:
        partial = result is not None and result.get("status") == "partial"
        event["message"] = (
            f"⚠️ 스크래핑 부분 실패: {job}"
            if partial
            else f"✅ 스크래핑 완료: {job}"
        )
    if result is not None:
        event["result"] = {**result, "job": job}
    return event


async def run_pipeline(scraper_type: str, job: str, scrape_mode: str = "default"):
    """실제 파이프라인 실행 함수"""
    try:
        # WebSocket 매니저 import
        from app.ws.manager import manager

        mode_labels = {
            "default": "기본",
            "incremental": "증분 수집",
            "full": "전체 수집",
        }

        # 시작 메시지
        await manager.send_message(
            json.dumps(
                {
                    "type": "status",
                    "message": f"🚀 스크래핑 시작: {job} ({mode_labels.get(scrape_mode, scrape_mode)})",
                    "progress": 0,
                }
            )
        )

        # uv run 명령어로 파이프라인 실행 (환경변수로 직무/모드 전달)
        import os

        env = os.environ.copy()
        env["SELECTED_JOB"] = job
        env["SCRAPE_MODE"] = scrape_mode
        env["PYTHONUNBUFFERED"] = "1"

        cmd = ["uv", "run", "app/cli.py"]
        if scrape_mode == "incremental":
            cmd.append("--incremental")
        elif scrape_mode == "full":
            cmd.append("--full")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # 프로세스를 매니저에 등록
        manager.set_scraping_process(process)

        # 프로세스 시작 확인 메시지
        await manager.send_message(
            json.dumps(
                {"type": "log", "message": f"프로세스 시작됨 (PID: {process.pid})"}
            )
        )

        pipeline_result = None

        # 실시간 출력/에러 읽기 함수들
        async def read_stdout():
            nonlocal pipeline_result
            try:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_text = line.decode("utf-8").strip()
                    parsed = parse_pipeline_result(line_text)
                    if parsed is not None:
                        pipeline_result = parsed
                    elif line_text:
                        await manager.send_message(
                            json.dumps({"type": "log", "message": line_text})
                        )
            except Exception as e:
                print(f"stdout 읽기 에러: {e}")

        async def read_stderr():
            try:
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    line_text = line.decode("utf-8").strip()
                    if line_text:
                        # stderr 출력도 그대로 표시 (로거 포맷에 이미 레벨 정보 포함)
                        await manager.send_message(
                            json.dumps({"type": "log", "message": line_text})
                        )
            except Exception as e:
                print(f"stderr 읽기 에러: {e}")

        # 출력 읽기 태스크들 생성
        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())

        # 프로세스 완료 대기
        returncode = await wait_for_exit(process)

        # 종료 직전 출력까지 읽는다 (넘으면 wait_for가 읽기를 취소한다)
        try:
            await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task),
                timeout=OUTPUT_DRAIN_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            print("출력 읽기 시간 초과: 남은 출력을 버립니다")

        # 스크래핑 완료 시 상태 리셋
        manager.is_scraping = False
        manager.current_process = None

        await manager.send_message(
            json.dumps(build_finish_event(job, returncode, pipeline_result))
        )

    except Exception as e:
        from app.ws.manager import manager

        await manager.send_message(
            json.dumps({"type": "error", "message": f"파이프라인 실행 에러: {e}"})
        )


@router.post("/stop")
async def stop_scraping():
    """스크래핑 중지"""
    try:
        from app.ws.manager import manager

        if manager.stop_scraping():
            await manager.send_message(
                json.dumps(
                    {"type": "stopped", "message": "⏹️ 스크래핑이 중지되었습니다"}
                )
            )
            return {"message": "스크래핑이 중지되었습니다"}
        else:
            return {"message": "실행 중인 스크래핑이 없습니다"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=ScrapingStatusResponse)
async def get_scraping_status() -> ScrapingStatusResponse:
    """스크래핑 상태 조회"""
    try:
        from app.ws.manager import manager

        return ScrapingStatusResponse(
            is_scraping=manager.is_scraping,
            has_process=manager.current_process is not None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
