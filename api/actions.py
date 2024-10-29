from fastapi import Depends
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.websockets import WebSocket

from api.auth import (
    blacklist_token,
    create_jwt_token,
    get_current_user_via_websocket,
    get_password_hash,
    is_token_blacklisted,
    oauth2_scheme,
    verify_token,
    verify_user,
)
from api.crud.chat import get_chats_for_user
from api.crud.user import create_user, get_user_by_email
from api.exceptions import WebSocketValidationException
from api.models import Chat, Message, User
from api.schemas.auth import AuthResponse, LoginData, RegisterData
from api.schemas.chat import (
    ChatCreate,
    ChatResponse,
    WebsocketChatCreateResponse,
    WebsocketChatResponse,
)
from api.schemas.message import MessageCreate, MessageResponse
from api.schemas.user import LoginForm, MeSchema, UserCreate
from engine import get_db
from utils.enums import WebSocketActions


async def check_blacklisted_token(action: str, db: AsyncSession, token: str):
    if await is_token_blacklisted(db, token):
        raise WebSocketValidationException(detail="Token is blacklisted", action=action)


async def register(user_create: UserCreate, db: AsyncSession):
    db_user = await get_user_by_email(db, user_create.email)
    if db_user:
        raise WebSocketValidationException(
            detail="This account is already registered!",
            action=WebSocketActions.REGISTER,
        )

    hashed_password = get_password_hash(user_create.password)
    await create_user(db, user_create.email, user_create.nickname, hashed_password)

    access_token = create_jwt_token(user_create.email)
    return AuthResponse(
        data=RegisterData(
            access_token=access_token,
            token_type="bearer",
        )
    )


async def login(login_form: LoginForm, db: AsyncSession):
    user = await verify_user(db, login_form.email, login_form.password)
    if not user:
        raise WebSocketValidationException(
            detail="Incorrect username or password!",
            action=WebSocketActions.LOGIN,
        )

    access_token = create_jwt_token(user.email)

    return AuthResponse(
        data=LoginData(
            access_token=access_token,
            token_type="bearer",
        )
    )


async def me(db: AsyncSession, token: str = Depends(oauth2_scheme)):
    await check_blacklisted_token(action=WebSocketActions.ME, db=db, token=token)
    try:
        email = verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.ME,
        )

    user = await get_user_by_email(db, email)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.ME,
        )

    return AuthResponse(data=MeSchema(email=user.email, nickname=user.nickname))


async def logout(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    await check_blacklisted_token(action=WebSocketActions.LOGOUT, db=db, token=token)
    try:
        verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.LOGOUT,
        )
    if not await is_token_blacklisted(db, token):
        await blacklist_token(db, token)


async def get_chats(websocket, db: AsyncSession, token: str):
    await check_blacklisted_token(action=WebSocketActions.GET_CHATS, db=db, token=token)
    user = await get_current_user_via_websocket(websocket, db=db, action=WebSocketActions.GET_CHATS)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.GET_CHATS,
        )
    return WebsocketChatResponse(data=await get_chats_for_user(user_uuid=user.uuid, db=db))


async def send_message(
    data: MessageCreate, websocket: WebSocket, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    await check_blacklisted_token(action=WebSocketActions.SEND_MESSAGE, db=db, token=token)
    sender = await get_current_user_via_websocket(websocket=websocket, db=db, action=WebSocketActions.SEND_MESSAGE)
    if not sender:
        raise WebSocketValidationException(
            detail="Sender not found!",
            action=WebSocketActions.SEND_MESSAGE,
        )

    chat = await db.get(Chat, data.chat_id)
    if not chat:
        raise WebSocketValidationException(
            detail="Chat not found!",
            action=WebSocketActions.SEND_MESSAGE,
        )

    message = Message(
        chat_id=data.chat_id,
        sender_id=sender.id,
        content=data.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        chat_id=message.chat_id,
        sender_email=sender.email,
        content=message.content,
        sent_at=message.sent_at.isoformat(),
    )


async def create_chat(
    data: ChatCreate, websocket: WebSocket, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    await check_blacklisted_token(action=WebSocketActions.CREATE_CHAT, db=db, token=token)
    creator = await get_current_user_via_websocket(websocket=websocket, db=db, action=WebSocketActions.CREATE_CHAT)
    if not creator:
        raise WebSocketValidationException(
            detail="Chat creator not found!",
            action=WebSocketActions.CREATE_CHAT,
        )

    participant = await get_user_by_email(db, data.participant_email)
    if not participant:
        raise WebSocketValidationException(
            detail="Chat participant not found!",
            action=WebSocketActions.CREATE_CHAT,
        )

    existing_chat_query = (
        select(Chat)
        .join(Chat.participants)
        .where(
            Chat.is_group == False,  # noqa
            Chat.participants.any(User.id == creator.id),
            Chat.participants.any(User.id == participant.id),
        )
    )
    print(f"{existing_chat_query=}")
    existing_chat_result = await db.execute(existing_chat_query)
    existing_chat = existing_chat_result.scalars().first()

    if existing_chat:
        raise WebSocketValidationException(
            detail="A chat already exists between these participants!",
            action=WebSocketActions.CREATE_CHAT,
        )

    chat = Chat(
        is_group=False,
    )
    chat.participants.append(creator)
    chat.participants.append(participant)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    return WebsocketChatCreateResponse(
        data=ChatResponse(
            id=chat.id,
            uuid=str(chat.uuid),
            participants=[str(creator.uuid), str(participant.uuid)],
            created_at=chat.created_at.isoformat(),
            display_name=participant.nickname,
        )
    )
