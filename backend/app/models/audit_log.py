from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    event_type = Column(String(30), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50))
    user_role = Column(String(20))
    operation = Column(String(20), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False, index=True)
    file_size_before = Column(BigInteger, nullable=True)
    file_size_after = Column(BigInteger, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    client_ip = Column(String(50))
    user_agent = Column(Text)
    session_id = Column(String(100))
    diff_content = Column(Text)
    error_message = Column(Text)
    event_metadata = Column(JSON)

    user = relationship("User", back_populates="audit_logs")
