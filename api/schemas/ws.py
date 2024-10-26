from pydantic import BaseModel

from enums import ResponseStatuses


class WebSocketResponseMessage(BaseModel):
    status: str = ResponseStatuses.OK
    data: dict
