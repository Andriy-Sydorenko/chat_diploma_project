from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from engine import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=True)  # For group chats
    is_group = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="chats")
    participants = relationship("ChatParticipant", back_populates="chat")
    messages = relationship("Message", back_populates="chat")

    def __repr__(self):
        return f"<Chat {self.name or self.id}>"


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    chat = relationship("Chat", back_populates="participants")
    user = relationship("User", back_populates="chat_participants")

    def __repr__(self):
        return f"<ChatParticipant {self.user_id} in Chat {self.chat_id}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")

    def __repr__(self):
        return f"<Message {self.id} in Chat {self.chat_id}>"
