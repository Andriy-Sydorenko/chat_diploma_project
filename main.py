import asyncio
from contextlib import asynccontextmanager
from pprint import pprint

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.params import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import (
    create_chat,
    get_chat_messages,
    get_chats_list,
    get_users,
    login,
    logout,
    me,
    register,
    send_message,
)
from api.auth import decrypt_jwt
from api.exceptions import WebSocketValidationException
from api.schemas.chat import ChatCreate
from api.schemas.message import GetChatMessages, MessageCreate
from api.schemas.user import UserCreate, UserLogin
from engine import get_db
from managers import manager
from utils.enums import SCHEMA_TO_ACTION_MAPPER, ResponseStatuses, WebSocketActions
from utils.utils import cleanup_blacklisted_tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    ping_pong_task = asyncio.create_task(ping_pong())
    yield
    ping_pong_task.cancel()
    async for db in get_db():
        await cleanup_blacklisted_tokens(db=db)


async def ping_pong():
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get("http://localhost:8000/ping")
            print(f"Health check response: {response.json()}")
            await asyncio.sleep(45)


app = FastAPI(
    lifespan=lifespan,
)


@app.get("/")
async def health_check():
    return {
        "status": "OK",
    }


@app.get("/ping")
async def ping():
    return {"message": "pong"}


@app.websocket("/")
async def check_connection(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data: dict = await manager.get_json(websocket)
            action = data.get("action")
            encrypted_token = data["data"].pop("token", "")
            if encrypted_token:
                token = decrypt_jwt(encrypted_token)
            else:
                token = None
            try:
                if action == WebSocketActions.REGISTER:
                    user_data = UserCreate(**data.get("data"))
                    response = await register(user_data, db, websocket)
                    pprint(manager.socket_to_user)

                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.LOGIN:
                    login_form = UserLogin(**data.get("data"))
                    response = await login(login_form, db, websocket)
                    pprint(manager.socket_to_user)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.LOGOUT:
                    await logout(websocket, token=token, db=db)
                    await websocket.send_json({"status": ResponseStatuses.OK, "message": "Successful logout!"})

                elif action == WebSocketActions.ME:
                    response = await me(token=token, db=db)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.GET_CHATS:
                    response = await get_chats_list(db=db, token=token)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.GET_USERS:
                    response = await get_users(db=db, token=token)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.CREATE_CHAT:
                    chat_data = ChatCreate(**data.get("data"))
                    response = await create_chat(chat_data, db, token=token)
                    await manager.send_json(response.dict(), websocket)
                elif action == WebSocketActions.GET_CHAT_MESSAGES:
                    chat_messages_data = GetChatMessages(**data.get("data"))
                    response = await get_chat_messages(chat_messages_data, db, token=token)
                    await manager.send_json(response.dict(), websocket)

                elif action == WebSocketActions.SEND_MESSAGE:
                    message_data = MessageCreate(**data.get("data"))
                    response = await send_message(message_data, db, token)
                    await manager.send_json(response.dict(), websocket)

            except ValidationError as exc:
                action = SCHEMA_TO_ACTION_MAPPER.get(exc.title)
                error = exc.errors()[0]
                field = error.get("loc")[0]
                detail = str(error.get("ctx").get("error"))
                wc_validation_exception = WebSocketValidationException(action=action, detail=detail, field=field)
                await manager.send_json(wc_validation_exception.to_dict(), websocket)
            except WebSocketValidationException as ws_exc:
                await manager.send_json(ws_exc.to_dict(), websocket)

    except WebSocketDisconnect:
        manager.socket_to_user.pop(websocket, None)
        manager.disconnect(websocket)
