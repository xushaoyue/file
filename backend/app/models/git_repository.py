from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class GitRepository(Base):
    __tablename__ = "git_repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    remote_url = Column(String(500), nullable=False)
    local_path = Column(String(500), nullable=False, unique=True)
    branch = Column(String(100), default="main")
    auth_type = Column(String(20), default="none")
    auth_credential = Column(String(500))
    status = Column(String(20), default="cloned")
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    commits = relationship("GitCommit", back_populates="repository", cascade="all, delete-orphan")
    webhook_config = relationship("GitWebhookConfig", back_populates="repository", uselist=False, cascade="all, delete-orphan")