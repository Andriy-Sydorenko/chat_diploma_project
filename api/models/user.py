from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from api.models.chat import user_chat_association
from engine import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    nickname = Column(String(60), nullable=False)
    hashed_password = Column(String, nullable=False)

    first_name = Column(String, index=True)
    last_name = Column(String, index=True)

    is_active = Column(Boolean, default=True)

    UniqueConstraint("email", name="uq_user_email")
    UniqueConstraint("nickname", name="uq_user_nickname")

    chats = relationship("Chat", secondary=user_chat_association, back_populates="participants")

    def __repr__(self):
        """Returns string representation of model instance"""
        return "<User {email!r}>".format(email=self.email)

    @property
    def full_name(self):
        """Returns the full name by concatenating first name and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return "First name or last name are undefined"
