from datetime import timedelta

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from api.auth import (
    authenticate_user,
    blacklist_token,
    create_access_token,
    get_current_user_via_websocket,
    get_password_hash,
    is_token_blacklisted,
    oauth2_scheme,
    verify_token,
)
from api.crud.user import create_user, get_user_by_email
from api.decorators import check_blacklisted_token
from api.schemas.user import LoginForm, UserCreate
from config import ACCESS_TOKEN_EXPIRATION_TIME
from engine import get_db
from managers import ConnectionManager
from test_html_file import html

app = FastAPI()
manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.post("/register/")
async def register(user_create: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user_create.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is already registered")

    hashed_password = get_password_hash(user_create.password)
    create_user(db, user_create.email, user_create.nickname, hashed_password)

    access_token = create_access_token(data={"sub": user_create.email})
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"msg": "User created successfully", "access_token": access_token, "token_type": "bearer"},
    )


@app.post("/login/")
async def login(login_form: LoginForm, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_form.email, login_form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRATION_TIME)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"access_token": access_token, "token_type": "bearer"})


@app.get("/me")
@check_blacklisted_token
async def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = verify_token(token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return JSONResponse(status_code=status.HTTP_200_OK, content={"email": user.email, "nickname": user.nickname})


@app.get("/logout")
async def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = verify_token(token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if not is_token_blacklisted(db, token):
        blacklist_token(db, token)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Successful logout!",
        },
    )


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, username: str = Depends(get_current_user_via_websocket)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.send_message(f"{username} left the chat")
