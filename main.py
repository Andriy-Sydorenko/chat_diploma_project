from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import (
    create_chat,
    get_chats,
    login,
    logout,
    me,
    register,
    send_message,
)
from api.exceptions import WebSocketValidationException
from api.schemas.chat import ChatCreate
from api.schemas.message import MessageCreate
from api.schemas.user import LoginForm, UserCreate
from engine import get_db
from managers import ConnectionManager
from utils.enums import ResponseStatuses, WebSocketActions

app = FastAPI()
manager = ConnectionManager()


@app.get("/")
async def health_check():
    return {
        "status": "OK",
    }


@app.websocket("/")
async def check_connection(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data = await manager.get_json(websocket)
            action = data.get("action")
            token = websocket.headers.get("Authorization")
            try:
                if action == WebSocketActions.REGISTER:
                    user_data = UserCreate(**data.get("data"))
                    response = await register(user_data, db)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.LOGIN:
                    login_form = LoginForm(**data.get("data"))
                    response = await login(login_form, db)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.LOGOUT:
                    await logout(token=token, db=db)
                    await websocket.send_json({"status": ResponseStatuses.OK, "message": "Successful logout!"})

                elif action == WebSocketActions.ME:
                    response = await me(token=token, db=db)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.GET_CHATS:
                    response = await get_chats(websocket=websocket, db=db, token=token)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.CREATE_CHAT:
                    chat_data = ChatCreate(**data.get("data"))
                    response = await create_chat(chat_data, websocket, db, token=token)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.SEND_MESSAGE:
                    message_data = MessageCreate(**data.get("data"))
                    response = await send_message(message_data, websocket, db)
                    await manager.send_json(response.dict(), websocket)

            except WebSocketValidationException as ws_exc:
                await manager.send_json(ws_exc.to_dict(), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
