from .db import Base
from sqlalchemy import (
    String,
    Column,
    JSON,
    DateTime,
    ForeignKey,
    func,
    Integer,
    Boolean,
)


class User(Base):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, primary_key=True)
    password = Column(String(255), nullable=True)
    name = Column(String(255))


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(255), primary_key=True)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    filename = Column(String(255), nullable=False)
    start_time = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    task_id = Column(String(255), nullable=False)
    extracted_data = Column(JSON(), nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
