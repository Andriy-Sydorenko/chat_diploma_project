from fastapi import Depends
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    blacklist_token,
    create_jwt_token,
    get_password_hash,
    is_token_blacklisted,
    oauth2_scheme,
    verify_token,
    verify_user,
)
from api.crud.user import create_user, get_user_by_email
from api.exceptions import WebSocketValidationException
from api.schemas.auth import AuthResponse, LoginData, RegisterData
from api.schemas.user import LoginForm, MeSchema, UserCreate
from engine import get_db
from utils.enums import WebSocketActions


async def check_blacklisted_token(action: str, db: AsyncSession, token: str):
    if await is_token_blacklisted(db, token):
        raise WebSocketValidationException(detail="Token is blacklisted", action=action)


async def register(user_create: UserCreate, db: AsyncSession):
    db_user = await get_user_by_email(db, user_create.email)
    if db_user:
        raise WebSocketValidationException(
            detail="This account is already registered!",
            action=WebSocketActions.REGISTER,
        )

    hashed_password = get_password_hash(user_create.password)
    await create_user(db, user_create.email, user_create.nickname, hashed_password)

    access_token = create_jwt_token(user_create.email)
    return AuthResponse(
        data=RegisterData(
            access_token=access_token,
            token_type="bearer",
        )
    )


async def login(login_form: LoginForm, db: AsyncSession):
    user = await verify_user(db, login_form.email, login_form.password)
    if not user:
        raise WebSocketValidationException(
            detail="Incorrect username or password!",
            action=WebSocketActions.LOGIN,
        )

    access_token = create_jwt_token(user.email)

    return AuthResponse(
        data=LoginData(
            access_token=access_token,
            token_type="bearer",
        )
    )


async def me(db: AsyncSession, token: str = Depends(oauth2_scheme)):
    await check_blacklisted_token(action="me", db=db, token=token)
    try:
        email = verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.ME,
        )

    user = await get_user_by_email(db, email)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.ME,
        )

    return AuthResponse(data=MeSchema(email=user.email, nickname=user.nickname))


async def logout(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    await check_blacklisted_token(action="logout", db=db, token=token)
    try:
        verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.LOGOUT,
        )
    if not await is_token_blacklisted(db, token):
        await blacklist_token(db, token)
