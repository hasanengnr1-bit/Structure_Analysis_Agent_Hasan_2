from sqlalchemy import String, Column, JSON, DateTime, ForeignKey, func
from .db import Base


class User(Base):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, primary_key=True)
    password = Column(String(255), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(255), primary_key=True)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    filename = Column(String(255), nullable=False)
    start_time = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    extracted_data = Column(JSON(), nullable=True)
