from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketState
import os
import subprocess

from backend.core.database import init_database
from backend.ws.manager import ConnectionManager, manager
from backend.api.routes import (
    dashboard,
    job_postings,
    labeling,
    scraping,
    statistics,
    companies,
    label_studio_webhook,
)


app = FastAPI(title="Job Scraper Dashboard", version="1.0.0")

# Enable CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files 마운트
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

app.include_router(dashboard.router)
app.include_router(job_postings.router)
app.include_router(scraping.router)
app.include_router(statistics.router)
app.include_router(companies.router)
app.include_router(labeling.router)
app.include_router(label_studio_webhook.router)

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

    dashboard_page = os.path.join(
        os.path.dirname(__file__), "templates", "dashboard.html"
    )
    with open(dashboard_page, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
