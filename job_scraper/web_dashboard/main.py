from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketState
import os
import subprocess

from job_scraper.database.connection import init_database
from job_scraper.web_dashboard.api.v1 import dashboard, job_postings, scraping, statistic, companies

# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.current_process = None  # 현재 실행 중인 프로세스
        self.is_scraping = False     # 스크래핑 상태

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections[:]:  # 복사본으로 순회
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message)
                except Exception:
                    self.active_connections.remove(connection)
    
    def set_scraping_process(self, process):
        """스크래핑 프로세스 설정"""
        self.current_process = process
        self.is_scraping = True
    
    def stop_scraping(self, timeout: int = 5):
        """스크래핑 중지"""
        if self.current_process and self.is_scraping:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=timeout)
                self.is_scraping = False
                return True
            except subprocess.TimeoutExpired:
                self.current_process.kill()
                self.is_scraping = False
                return True
            except Exception:
                pass
        return False

manager = ConnectionManager()

app = FastAPI(title="Job Scraper Dashboard", version="1.0.0")

# Static files 마운트
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), 
                                                        "static")), name="static")

app.include_router(dashboard.router)
app.include_router(job_postings.router)
app.include_router(scraping.router)
app.include_router(statistic.router)
app.include_router(companies.router)

# 데이터베이스 초기화
init_database()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # 연결 유지
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """대시보드 메인 페이지"""
    
    dashboard_page = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    with open(dashboard_page, 'r', encoding='utf-8') as f: 
        return HTMLResponse(content=f.read())
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)