from pydantic import BaseModel, EmailStr, constr


class UserCreate(BaseModel):
    email: EmailStr
    nickname: constr(min_length=1, max_length=60)
    password: constr(min_length=8)
