import base64
import os
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError, PyJWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.crud.user import get_user_by_email
from api.exceptions import WebSocketValidationException
from api.models.token import BlacklistedToken
from utils.config import (
    ACCESS_TOKEN_EXPIRATION_TIME,
    ENCRYPTION_ALGORITHM,
    IV_LENGTH,
    JWT_AES_KEY,
    JWT_SECRET,
    TAG_LENGTH,
)

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


async def get_current_user_via_websocket(token: str, db: AsyncSession, action: str):
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


def encrypt_jwt(jwt_token):
    # Generate a random IV
    iv = os.urandom(IV_LENGTH)  # 12 bytes for GCM

    # Create a Cipher object
    cipher = Cipher(algorithms.AES(JWT_AES_KEY), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Encrypt the token
    ciphertext = encryptor.update(jwt_token.encode()) + encryptor.finalize()

    # Combine IV, ciphertext, and tag
    tag = encryptor.tag  # Get the authentication tag
    combined = iv + ciphertext + tag  # Combine them
    return base64.b64encode(combined).decode("utf-8")


def decrypt_jwt(encrypted_token):
    # Decode the base64 encoded token
    combined = base64.b64decode(encrypted_token)

    # Extract IV, ciphertext, and tag
    iv = combined[:IV_LENGTH]  # First 12 bytes are the IV
    tag = combined[-TAG_LENGTH:]  # Last 16 bytes are the tag
    ciphertext = combined[IV_LENGTH:-TAG_LENGTH]  # Remaining bytes are the ciphertext

    # Create a Cipher object
    cipher = Cipher(algorithms.AES(JWT_AES_KEY), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt the token
    decrypted_jwt = decryptor.update(ciphertext) + decryptor.finalize()

    return decrypted_jwt.decode("utf-8")
