from pydantic import BaseModel, EmailStr

from api.schemas.ws import WebSocketResponseMessage


class ChatCreate(BaseModel):
    participant_email: EmailStr


class ChatListResponse(BaseModel):
    uuid: str
    participants: list[str]
    created_at: str
    display_name: str


class WebsocketChatResponse(WebSocketResponseMessage):
    data: dict[str, list[ChatListResponse]]


class WebsocketChatCreateResponse(WebSocketResponseMessage):
    data: ChatListResponse
