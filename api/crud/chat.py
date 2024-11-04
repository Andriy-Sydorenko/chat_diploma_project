from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from api.models import Chat, Message, User
from api.schemas.chat import ChatListResponse
from api.schemas.message import MessageResponse


async def get_chats_for_user(user_uuid: int, db: AsyncSession) -> list[ChatListResponse]:
    query = (
        select(Chat).options(selectinload(Chat.participants)).join(Chat.participants).filter(User.uuid == user_uuid)
    )
    result = await db.execute(query)
    chats = result.scalars().all()

    chat_responses = []
    for chat in chats:
        other_participant = next(participant for participant in chat.participants if participant.uuid != user_uuid)
        chat_responses.append(
            ChatListResponse(
                uuid=str(chat.uuid),
                participants=[str(p.uuid) for p in chat.participants],
                created_at=chat.created_at.isoformat(),
                display_name=other_participant.nickname,
            )
        )

    return chat_responses


async def get_chat_messages(chat_uuid: str, db: AsyncSession):
    chat = await db.execute(
        select(Chat).options(selectinload(Chat.messages).selectinload(Message.sender)).where(Chat.uuid == chat_uuid)
    )
    chat = chat.scalars().first()
    if not chat:
        return None

    messages = chat.messages
    return [
        MessageResponse(
            chat_uuid=str(chat.uuid),
            sender_uuid=str(message.sender.uuid),
            content=message.content,
            sent_at=message.sent_at.isoformat(),
        )
        for message in messages
    ]
