from pydantic import BaseModel, EmailStr

from api.schemas.ws import WebSocketResponseMessage


class ChatCreate(BaseModel):
    participant_email: EmailStr


class ChatResponse(BaseModel):
    id: int
    uuid: str
    participants: list[str]
    created_at: str
    display_name: str


class WebsocketChatResponse(WebSocketResponseMessage):
    data: list[ChatResponse]


class WebsocketChatCreateResponse(WebSocketResponseMessage):
    data: ChatResponse
