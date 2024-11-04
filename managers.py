import uuid
from typing import Dict, Optional

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.socket_to_user: Dict[WebSocket, Optional[uuid.UUID]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.socket_to_user[websocket] = None

    @staticmethod
    async def get_json(websocket: WebSocket):
        return await websocket.receive_json()

    @staticmethod
    async def send_json(data: dict, websocket: WebSocket):
        return await websocket.send_json(data)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        websocket.close()

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()
