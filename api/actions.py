from fastapi import Depends
from jwt import PyJWTError
from sqlalchemy.orm import Session

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
from api.schemas.user import LoginForm, UserCreate
from engine import get_db
from enums import WebSocketActions


def check_blacklisted_token(action: str, db: Session, token: str):
    if is_token_blacklisted(db, token):
        raise WebSocketValidationException(detail="Token is blacklisted", action=action)


async def register(user_create: UserCreate, db: Session):
    db_user = get_user_by_email(db, user_create.email)
    if db_user:
        raise WebSocketValidationException(
            detail="This account is already registered!",
            action=WebSocketActions.REGISTER,
        )

    hashed_password = get_password_hash(user_create.password)
    create_user(db, user_create.email, user_create.nickname, hashed_password)

    access_token = create_jwt_token(user_create.email)
    return {"data": {"message": "User created successfully", "access_token": access_token, "token_type": "bearer"}}


async def login(login_form: LoginForm, db: Session):
    user = verify_user(db, login_form.email, login_form.password)
    if not user:
        raise WebSocketValidationException(
            detail="Incorrect username or password!",
            action=WebSocketActions.LOGIN,
        )

    access_token = create_jwt_token(user.email)

    return {"access_token": access_token, "token_type": "bearer"}


async def me(db: Session, token: str = Depends(oauth2_scheme)):
    check_blacklisted_token(action="me", db=db, token=token)
    try:
        email = verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.ME,
        )

    user = get_user_by_email(db, email)
    if not user:
        raise WebSocketValidationException(
            detail="User not found!",
            action=WebSocketActions.ME,
        )

    return {"email": user.email, "nickname": user.nickname}


async def logout(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    check_blacklisted_token(action="logout", db=db, token=token)
    try:
        verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(
            detail="Invalid token!",
            action=WebSocketActions.LOGOUT,
        )
    if not is_token_blacklisted(db, token):
        blacklist_token(db, token)
