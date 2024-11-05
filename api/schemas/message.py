from pydantic import BaseModel

from api.schemas.ws import WebSocketResponseMessage


class MessageCreate(BaseModel):
    chat_uuid: str
    content: str


class GetChatMessages(BaseModel):
    chat_uuid: str


class MessageResponse(BaseModel):
    chat_uuid: str
    sender_uuid: str
    sender_nickname: str
    content: str
    sent_at: str


class WebsocketMessagesResponse(WebSocketResponseMessage):
    data: list[MessageResponse]


class WebsocketMessageCreateResponse(WebSocketResponseMessage):
    data: MessageResponse
