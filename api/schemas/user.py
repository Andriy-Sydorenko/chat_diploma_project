from pydantic import BaseModel, constr, field_validator

from api.schemas.ws import WebSocketResponseMessage


class EmailPasswordValidation(BaseModel):
    @field_validator("email", check_fields=False)
    def validate_email(cls, value: str) -> str:
        parts = value.split("@")
        if len(parts) != 2 or "." not in parts[1]:
            raise ValueError("Email must be in the format 'x@y.com' with only one character before '@'.")
        return value

    @field_validator("password", check_fields=False)
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit.")
        if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/~`" for char in value):
            raise ValueError("Password must contain at least one special character.")
        if any(char.isspace() for char in value):
            raise ValueError("Password must not contain any whitespace.")

        return value


class UserCreate(EmailPasswordValidation):
    email: str
    nickname: constr(min_length=1, max_length=60)
    password: str


class UserLogin(EmailPasswordValidation):
    email: str
    password: str


class MeSchema(BaseModel):
    email: str
    nickname: str
    user_uuid: str


class UserListResponse(BaseModel):
    email: str
    nickname: str
    uuid: str


class WebsocketUserResponse(WebSocketResponseMessage):
    data: dict[str, list[UserListResponse]]
