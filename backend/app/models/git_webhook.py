from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class GitWebhookConfig(Base):
    __tablename__ = "git_webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("git_repositories.id"), nullable=False, index=True)
    webhook_secret = Column(String(100))
    provider = Column(String(20))
    enabled = Column(Boolean, default=True)
    auto_pull = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    repository = relationship("GitRepository", back_populates="webhook_config")