from functools import wraps

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import is_token_blacklisted, oauth2_scheme
from engine import get_db


def check_blacklisted_token(endpoint_func):
    @wraps(endpoint_func)
    async def wrapper(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme), *args, **kwargs):
        # Check if the token is blacklisted
        if is_token_blacklisted(db, token):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is blacklisted")
        # Proceed to endpoint if token is not blacklisted
        return await endpoint_func(db=db, token=token, *args, **kwargs)

    return wrapper
