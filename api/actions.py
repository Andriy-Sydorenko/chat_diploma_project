from pprint import pprint
from uuid import UUID

from fastapi import Depends, WebSocket
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from api.auth import (
    blacklist_token,
    create_jwt_token,
    encrypt_jwt,
    get_current_user_via_websocket,
    get_password_hash,
    is_token_blacklisted,
    oauth2_scheme,
    verify_token,
    verify_user,
)
from api.crud import chat as chat_crud
from api.crud import user as user_crud
from api.exceptions import WebSocketValidationException
from api.models import Chat, Message, User
from api.schemas.auth import AuthResponse, LoginData, RegisterData
from api.schemas.chat import (
    ChatCreate,
    ChatListResponse,
    WebsocketChatCreateResponse,
    WebsocketChatResponse,
)
from api.schemas.message import (
    GetChatMessages,
    MessageCreate,
    MessageResponse,
    WebsocketMessageCreateResponse,
    WebsocketMessagesResponse,
)
from api.schemas.user import MeSchema, UserCreate, UserLogin, WebsocketUserResponse
from engine import get_db
from managers import manager
from utils.enums import WebSocketActions
from utils.utils import remove_websocket_by_value


async def check_blacklisted_token(action: str, db: AsyncSession, token: str):
    if await is_token_blacklisted(db, token):
        raise WebSocketValidationException(detail="Token is blacklisted", action=action)


async def register(user_create: UserCreate, db: AsyncSession, websocket: WebSocket):
    db_user = await user_crud.get_user_by_email(db, user_create.email)
    if db_user:
        raise WebSocketValidationException(
            detail="This account is already registered!",
            action=WebSocketActions.REGISTER,
        )

    hashed_password = get_password_hash(user_create.password)
    registered_user = await user_crud.create_user(db, user_create.email, user_create.nickname, hashed_password)

    access_token = create_jwt_token(user_create.email)
    encrypted_token = encrypt_jwt(access_token)
    manager.socket_to_user[registered_user.uuid] = websocket

    return AuthResponse(
        action=WebSocketActions.REGISTER,
        data=RegisterData(
            access_token=encrypted_token,
        ),
    )


async def login(login_form: UserLogin, db: AsyncSession, websocket: WebSocket):
    user = await verify_user(db, login_form.email, login_form.password)
    if not user:
        raise WebSocketValidationException(
            detail="Incorrect username or password!",
            action=WebSocketActions.LOGIN,
        )

    access_token = create_jwt_token(user.email)
    encrypted_token = encrypt_jwt(access_token)

    manager.socket_to_user[user.uuid] = websocket

    return AuthResponse(
        action=WebSocketActions.LOGIN,
        data=LoginData(
            access_token=encrypted_token,
        ),
    )


async def login_REST(login_form: UserLogin, db: AsyncSession):
    user = await verify_user(db, login_form.email, login_form.password)
    if not user:
        raise WebSocketValidationException(
            detail="Incorrect username or password!",
            action=WebSocketActions.LOGIN,
        )

    access_token = create_jwt_token(user.email)
    encrypted_token = encrypt_jwt(access_token)

    return AuthResponse(
        action=WebSocketActions.LOGIN,
        data=LoginData(
            access_token=encrypted_token,
        ),
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

    user = await user_crud.get_user_by_email(db, email)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.ME,
        )

    return AuthResponse(
        action=WebSocketActions.ME, data=MeSchema(email=user.email, nickname=user.nickname, user_uuid=str(user.uuid))
    )


async def logout(websocket: WebSocket, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    await check_blacklisted_token(action=WebSocketActions.LOGOUT, db=db, token=token)
    try:
        verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.LOGOUT,
        )

    remove_websocket_by_value(manager.socket_to_user, websocket)

    if not await is_token_blacklisted(db, token):
        await blacklist_token(db, token)


async def get_chats_list(db: AsyncSession, token: str):
    await check_blacklisted_token(action=WebSocketActions.GET_CHATS, db=db, token=token)
    user = await get_current_user_via_websocket(token=token, db=db, action=WebSocketActions.GET_CHATS)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.GET_CHATS,
        )
    return WebsocketChatResponse(
        action=WebSocketActions.GET_CHATS,
        data={"chats": await chat_crud.get_chats_for_user(user_uuid=user.uuid, db=db)},
    )


async def get_users(db: AsyncSession, token: str):
    await check_blacklisted_token(action=WebSocketActions.GET_USERS, db=db, token=token)
    user = await get_current_user_via_websocket(token=token, db=db, action=WebSocketActions.GET_CHATS)
    pprint(manager.socket_to_user)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.GET_USERS,
        )
    return WebsocketUserResponse(
        action=WebSocketActions.GET_USERS,
        data={"users": await user_crud.get_users_list(request_user_uuid=user.uuid, db=db)},
    )


async def send_message(data: MessageCreate, db: AsyncSession, token: str):
    await check_blacklisted_token(action=WebSocketActions.SEND_MESSAGE, db=db, token=token)
    sender = await get_current_user_via_websocket(token=token, db=db, action=WebSocketActions.SEND_MESSAGE)
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
        chat_uuid=chat.uuid,
        sender_uuid=sender.uuid,
        content=data.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    other_participant = next(participant for participant in chat.participants if participant.id != sender.id)
    other_participant_websocket = next(
        (ws for uuid, ws in manager.socket_to_user.items() if uuid == other_participant.uuid), None
    )
    print(f"{manager.socket_to_user.items()=}")
    if other_participant_websocket:
        print(f"DONE: {other_participant_websocket=}")
        await manager.send_json(
            {
                "action": WebSocketActions.NEW_MESSAGE_RECEIVED,
                "data": {
                    "id": message.id,
                    "chat_uuid": str(chat.uuid),
                    "sender_uuid": str(sender.uuid),
                    "content": message.content,
                    "sent_at": message.sent_at.isoformat(),
                },
            },
            other_participant_websocket,
        )

    return WebsocketMessageCreateResponse(
        action=WebSocketActions.SEND_MESSAGE,
        data=MessageResponse(
            chat_uuid=str(message.chat_uuid),
            sender_uuid=str(sender.uuid),
            sender_nickname=sender.nickname,
            content=message.content,
            sent_at=message.sent_at.isoformat(),
        ),
    )


async def create_chat(data: ChatCreate, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    await check_blacklisted_token(action=WebSocketActions.CREATE_CHAT, db=db, token=token)
    creator = await get_current_user_via_websocket(token=token, db=db, action=WebSocketActions.CREATE_CHAT)
    if not creator:
        raise WebSocketValidationException(
            detail="Chat creator not found!",
            action=WebSocketActions.CREATE_CHAT,
        )

    participant = await user_crud.get_user_by_email(db, data.participant_email)
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
        action=WebSocketActions.CREATE_CHAT,
        data=ChatListResponse(
            uuid=str(chat.uuid),
            participants=[str(creator.uuid), str(participant.uuid)],
            created_at=chat.created_at.isoformat(),
            display_name=participant.nickname,
        ),
    )


async def get_chat_messages(chat_messages_data: GetChatMessages, db: AsyncSession, token: str):
    await check_blacklisted_token(action=WebSocketActions.CREATE_CHAT, db=db, token=token)
    chat_messages = await chat_crud.get_chat_messages(chat_uuid=chat_messages_data.chat_uuid, db=db)

    return WebsocketMessagesResponse(action=WebSocketActions.GET_CHAT_MESSAGES, data=chat_messages)
