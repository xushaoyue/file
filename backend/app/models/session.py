from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True)
    refresh_token_hash = Column(String(255))
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(50))
    user_agent = Column(Text)

    user = relationship("User", back_populates="sessions")
