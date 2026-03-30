"""
스크래핑 작업에 관련된 기능
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
import subprocess
import asyncio
import json
from typing import Optional

from app.schemas.scraping import (
    ScrapingRequest,
    ScrapingResponse,
    ScrapingStatusResponse,
)


router = APIRouter(prefix="/api/scraping", tags=["scraping"])


@router.post("/start", response_model=ScrapingResponse)
async def start_scraping(
    request: ScrapingRequest, background_tasks: BackgroundTasks
) -> ScrapingResponse:
    """스크래핑 파이프라인 시작"""
    try:
        # 백그라운드에서 파이프라인 실행
        background_tasks.add_task(run_pipeline, request.scraper_type, request.job)

        return ScrapingResponse(
            message="스크래핑이 시작되었습니다",
            scraper_type=request.scraper_type,
            job=request.job,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_pipeline(scraper_type: str, job: str):
    """실제 파이프라인 실행 함수"""
    try:
        # WebSocket 매니저 import
        from app.ws.manager import manager

        # 시작 메시지
        await manager.send_message(
            json.dumps(
                {"type": "status", "message": f"🚀 스크래핑 시작: {job}", "progress": 0}
            )
        )

        # 디버깅 메시지
        await manager.send_message(
            json.dumps(
                {"type": "log", "message": f"명령어 실행: uv run backend/cli.py"}
            )
        )

        # uv run 명령어로 파이프라인 실행 (환경변수로 직무 전달)
        import os

        env = os.environ.copy()
        env["SELECTED_JOB"] = job  # 환경변수로 직무 전달
        env["PYTHONUNBUFFERED"] = "1"  # Python 출력 버퍼링 비활성화

        cmd = ["uv", "run", "backend/cli.py"]

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

        # 실시간 출력/에러 읽기 함수들
        async def read_stdout():
            try:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_text = line.decode("utf-8").strip()
                    if line_text:
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
        returncode = await process.wait()

        # 태스크들 정리
        stdout_task.cancel()
        stderr_task.cancel()

        # 스크래핑 완료 시 상태 리셋
        manager.is_scraping = False
        manager.current_process = None

        if returncode == 0:
            await manager.send_message(
                json.dumps(
                    {
                        "type": "complete",
                        "message": f"✅ 스크래핑 완료: {job}",
                        "progress": 100,
                    }
                )
            )
        else:
            await manager.send_message(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"❌ 스크래핑 실패 (종료 코드: {returncode})",
                    }
                )
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
