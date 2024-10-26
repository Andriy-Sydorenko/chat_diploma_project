from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from api.actions import login, logout, me, register
from api.exceptions import WebSocketValidationException
from api.schemas.user import LoginForm, UserCreate
from engine import SessionLocal
from enums import WebSocketActions
from managers import ConnectionManager
from test_html_file import html

app = FastAPI()
manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/")
async def check_connection(websocket: WebSocket):
    await manager.connect(websocket)
    db = SessionLocal()
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
                    await websocket.send_text("Successful logout!")

                elif action == WebSocketActions.ME:
                    response = await me(token=token, db=db)
                    await manager.send_json(response.dict(), websocket)

            except WebSocketValidationException as ws_exc:
                await manager.send_json(ws_exc.to_dict(), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.send_message("Connection closed")
    finally:
        db.close()
