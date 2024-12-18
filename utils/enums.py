from enum import Enum


class EncryptionAlgorithms(str, Enum):
    # HMAC (Symmetric) Algorithms
    HS256 = "HS256"
    HS384 = "HS384"
    HS512 = "HS512"

    # RSA (Asymmetric) Algorithms
    RS256 = "RS256"
    RS384 = "RS384"
    RS512 = "RS512"

    # ECDSA (Asymmetric) Algorithms
    ES256 = "ES256"
    ES384 = "ES384"
    ES512 = "ES512"

    # No Signature
    NONE = "none"


class WebSocketActions(str, Enum):
    REGISTER = "REGISTER"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    GET_CHATS = "GET_CHATS"
    GET_USERS = "GET_USERS"
    CREATE_CHAT = "CREATE_CHAT"
    SEND_MESSAGE = "SEND_MESSAGE"
    GET_CHAT_MESSAGES = "GET_CHAT_MESSAGES"
    ME = ("ME",)

    NEW_MESSAGE_RECEIVED = "NEW_MESSAGE_RECEIVED"


SCHEMA_TO_ACTION_MAPPER = {
    "UserLogin": WebSocketActions.LOGIN,
    "UserCreate": WebSocketActions.REGISTER,
    "UserListResponse": WebSocketActions.GET_USERS,
}


class ResponseStatuses(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
