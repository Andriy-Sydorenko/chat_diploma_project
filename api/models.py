from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)

from engine import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    nickname = Column(String(60), nullable=False)
    hashed_password = Column(LargeBinary, nullable=False)

    first_name = Column(String, index=True)
    last_name = Column(String, index=True)

    is_active = Column(Boolean, default=True)

    UniqueConstraint("email", name="uq_user_email")
    PrimaryKeyConstraint("id", name="pk_user_id")

    def __repr__(self):
        """Returns string representation of model instance"""
        return "<User {full_name!r}>".format(full_name=self.full_name)

    @property
    def full_name(self):
        """Returns the full name by concatenating first name and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return "First name or last name are undefined"
