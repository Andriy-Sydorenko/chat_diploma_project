from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import jwt
from fastapi import WebSocket
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError, PyJWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.crud.user import get_user_by_email
from api.exceptions import WebSocketValidationException
from api.models.token import BlacklistedToken
from utils.config import ACCESS_TOKEN_EXPIRATION_TIME, ENCRYPTION_ALGORITHM, JWT_SECRET

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_jwt_token(email: str):
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRATION_TIME),
        "jti": token_urlsafe(16),
    }

    token = jwt.encode(payload, JWT_SECRET, ENCRYPTION_ALGORITHM)
    return token


def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[
                ENCRYPTION_ALGORITHM,
            ],
            options={"require": ["exp", "iat", "nbf"]},
        )
        email: str = payload["sub"]
        return email

    except ExpiredSignatureError:
        raise PyJWTError("Token is expired!")
    except DecodeError:
        # Raised when there is an error decoding the token (e.g., tampered signature)
        raise PyJWTError("Token decode problem!")
    except InvalidTokenError:
        raise PyJWTError("Token is invalid!")


async def get_current_user_via_websocket(websocket: WebSocket, db: AsyncSession, action: str):
    token = websocket.query_params.get("auth")
    if token is None:
        raise WebSocketValidationException(detail="Token is missing", action=action)

    try:
        email = verify_token(token)
    except PyJWTError:
        raise WebSocketValidationException(detail="Invalid token", action=action)

    user = await get_user_by_email(db, email)
    if not user:
        raise WebSocketValidationException(detail="User not found", action=action)

    return user


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def verify_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email=email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def blacklist_token(db: AsyncSession, token: str):
    blacklisted_token = BlacklistedToken(token=token)
    db.add(blacklisted_token)
    await db.commit()


async def is_token_blacklisted(db: AsyncSession, token: str = "") -> bool:
    query = select(BlacklistedToken).where(BlacklistedToken.token == token)
    result = await db.execute(query)
    return result.scalars().first() is not None
