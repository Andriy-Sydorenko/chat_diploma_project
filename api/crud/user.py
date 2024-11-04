from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from api.models import Chat
from api.models.user import User
from api.schemas.user import UserListResponse


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalars().first()


async def get_user_by_uuid(db: AsyncSession, uuid: str) -> Optional[User]:
    query = select(User).where(User.uuid == uuid)
    result = await db.execute(query)
    return result.scalars().first()


async def get_users_list(request_user_uuid: User, db: AsyncSession):
    users = await db.execute(select(User).filter(User.is_active == True, User.uuid != request_user_uuid))  # noqa
    users = users.scalars().all()

    chats_query = (
        select(Chat)
        .options(joinedload(Chat.participants))
        .join(Chat.participants)
        .filter(User.uuid == request_user_uuid)
    )
    chats_result = await db.execute(chats_query)
    chats = chats_result.unique().scalars().all()

    # Collect UUIDs of users who are participants in any chat with the requesting user
    excluded_user_uuids = {
        participant.uuid
        for chat in chats
        for participant in chat.participants
        if participant.uuid != request_user_uuid
    }

    # Filter out users who are in the excluded_user_uuids set
    filtered_users = [user for user in users if user.uuid not in excluded_user_uuids]

    return [UserListResponse(email=user.email, nickname=user.nickname, uuid=str(user.uuid)) for user in filtered_users]


async def create_user(db: AsyncSession, email: str, nickname: str, hashed_password: str):
    db_user = User(email=email, nickname=nickname, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
