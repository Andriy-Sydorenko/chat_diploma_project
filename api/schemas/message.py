from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessageCreate(BaseModel):
    chat_id: int
    sender_uuid: str
    content: str


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_uuid: UUID
    content: str
    sent_at: datetime
