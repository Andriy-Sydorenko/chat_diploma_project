from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from engine import Base


class BlacklistedToken(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    token = Column(String, nullable=False)
    blacklisted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
