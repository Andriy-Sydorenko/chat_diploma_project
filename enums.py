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
    REGISTER = "register"
    LOGIN = "login"
    LOGOUT = "logout"
    SEND_MESSAGE = "send_message"
    ME = "me"
