from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import subprocess


# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.current_process = None  # 현재 실행 중인 프로세스
        self.is_scraping = False  # 스크래핑 상태

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
