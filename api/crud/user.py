from typing import Optional

from sqlalchemy.orm import Session

from api.models.user import User


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, nickname: str, hashed_password: str):
    db_user = User(email=email, nickname=nickname, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
