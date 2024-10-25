from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import jwt
from fastapi import HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError, PyJWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.crud.user import get_user_by_email
from api.models.token import BlacklistedToken
from config import ACCESS_TOKEN_EXPIRATION_TIME, ENCRYPTION_ALGORITHM, JWT_SECRET

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


async def get_current_user_via_websocket(websocket: WebSocket):
    token = websocket.headers.get("Authorization")
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # Policy violation (missing token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token is missing")

    try:
        email = verify_token(token)
    except PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # Policy violation (invalid token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    return email


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email=email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def blacklist_token(db: Session, token: str):
    blacklisted_token = BlacklistedToken(token=token)
    db.add(blacklisted_token)
    db.commit()


def is_token_blacklisted(db: Session, token: str) -> bool:
    return db.query(BlacklistedToken).filter(BlacklistedToken.token == token).first() is not None
