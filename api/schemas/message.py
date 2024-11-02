from pydantic import BaseModel

from api.schemas.ws import WebSocketResponseMessage


class MessageCreate(BaseModel):
    chat_uuid: str
    content: str


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_uuid: str
    content: str
    sent_at: str


class WebsocketMessagesResponse(WebSocketResponseMessage):
    data: list[MessageResponse]


class WebsocketMessageCreateResponse(WebSocketResponseMessage):
    data: MessageResponse
