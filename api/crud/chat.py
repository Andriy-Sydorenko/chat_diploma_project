from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from api.models import Chat, User
from api.schemas.chat import ChatListResponse


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
                id=chat.id,
                uuid=str(chat.uuid),
                participants=[str(p.uuid) for p in chat.participants],
                created_at=chat.created_at.isoformat(),
                display_name=other_participant.nickname,
            )
        )

    return chat_responses
