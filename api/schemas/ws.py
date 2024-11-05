from pydantic import BaseModel

from utils.enums import ResponseStatuses


class WebSocketResponseMessage(BaseModel):
    status: str = ResponseStatuses.OK
    action: str = "None"
    data: dict
