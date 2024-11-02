from uuid import UUID

from fastapi import Depends
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
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
from api.schemas.message import (
    MessageCreate,
    MessageResponse,
    WebsocketMessageCreateResponse,
)
from api.schemas.user import MeSchema, UserCreate, UserLogin
from engine import get_db
from managers import manager
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


async def login(login_form: UserLogin, db: AsyncSession):
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


async def send_message(data: MessageCreate, websocket: WebSocket, db: AsyncSession, token: str):
    await check_blacklisted_token(action=WebSocketActions.SEND_MESSAGE, db=db, token=token)
    sender = await get_current_user_via_websocket(websocket=websocket, db=db, action=WebSocketActions.SEND_MESSAGE)
    if not sender:
        raise WebSocketValidationException(
            detail="Sender not found!",
            action=WebSocketActions.SEND_MESSAGE,
        )
    try:
        chat_uuid = UUID(data.chat_uuid)
    except ValueError:
        raise WebSocketValidationException(
            detail="Invalid UUID format for chat_uuid!", action=WebSocketActions.SEND_MESSAGE
        )

    chat_query = select(Chat).options(selectinload(Chat.participants)).filter(Chat.uuid == chat_uuid)
    chat_result = await db.execute(chat_query)
    chat = chat_result.scalars().first()
    if not chat:
        raise WebSocketValidationException(
            detail="Chat not found!",
            action=WebSocketActions.SEND_MESSAGE,
        )

    message = Message(
        chat_id=chat.id,
        sender_id=sender.id,
        content=data.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    other_participant = next(participant for participant in chat.participants if participant.id != sender.id)
    print(f"{manager.active_connections=}")
    for connection in manager.active_connections:
        if (
            getattr(
                await get_current_user_via_websocket(connection, db=db, action=WebSocketActions.SEND_MESSAGE), "email"
            )
            == other_participant.email
        ):
            print("FUCK YEAH!!!!")
            await manager.send_json(
                {
                    "action": WebSocketActions.SEND_MESSAGE,
                    "data": {
                        "id": message.id,
                        "chat_id": message.chat_id,
                        "sender_email": sender.email,
                        "content": message.content,
                        "sent_at": message.sent_at.isoformat(),
                    },
                },
                connection,
            )

    return WebsocketMessageCreateResponse(
        data=MessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            sender_uuid=str(sender.uuid),
            content=message.content,
            sent_at=message.sent_at.isoformat(),
        )
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
