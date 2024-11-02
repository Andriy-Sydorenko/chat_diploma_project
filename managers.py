from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

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
