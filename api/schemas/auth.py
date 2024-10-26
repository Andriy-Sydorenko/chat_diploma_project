from pydantic import BaseModel

from api.schemas.user import MeSchema
from api.schemas.ws import WebSocketResponseMessage


class RegisterData(BaseModel):
    access_token: str
    token_type: str


class LoginData(BaseModel):
    access_token: str
    token_type: str


class AuthResponse(WebSocketResponseMessage):
    data: RegisterData | LoginData | MeSchema
