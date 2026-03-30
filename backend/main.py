from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.core.database import init_database
from backend.ws.manager import manager
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
