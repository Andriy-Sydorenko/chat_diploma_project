import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from engine import Base

user_chat_association = Table(
    "user_chat_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("chat_id", Integer, ForeignKey("chats.id"), primary_key=True),
)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)  # For group chats
    is_group = Column(Boolean, default=False)  # For group chats
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    participants = relationship("User", secondary=user_chat_association, back_populates="chats")
    messages = relationship("Message", back_populates="chat")

    def __repr__(self):
        return f"<Chat {self.name or self.id}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    chat_uuid = Column(UUID(as_uuid=True), ForeignKey("chats.uuid"), nullable=False)
    sender_uuid = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")

    def __repr__(self):
        return f"<Message {self.id} in Chat {self.chat_uuid}>"
