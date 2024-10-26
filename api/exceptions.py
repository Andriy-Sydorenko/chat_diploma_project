from utils.enums import ResponseStatuses


class WebSocketException(Exception):
    def __init__(self, detail: str, action: str = None, data: dict = None):
        self.detail = detail
        self.action = action
        self.data = data or {}

    def to_dict(self):
        return {
            "status": ResponseStatuses.ERROR,
            "action": self.action,
            "error": {"detail": self.detail, "data": self.data},
        }


class WebSocketAuthenticationException(WebSocketException):
    def __init__(self, detail: str = "Authentication failed", action: str = None):
        super().__init__(detail=detail, action=action)


class WebSocketValidationException(WebSocketException):
    def __init__(self, detail: str, action: str = None):
        super().__init__(
            detail=detail,
            action=action,
        )
