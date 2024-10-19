from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.crud.user import get_user_by_email
from config import ACCESS_TOKEN_EXPIRATION_TIME, ENCRYPTION_ALGORITHM, JWT_SECRET

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRATION_TIME)

    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm=ENCRYPTION_ALGORITHM)
    return token


def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ENCRYPTION_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError
        return username
    except JWTError:
        return None


async def get_current_user_via_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # Policy violation (missing token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token is missing")

    username = verify_token(token)
    if username is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # Policy violation (invalid token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    return username


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(email: str, password: str):
    user = get_user_by_email()
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user
