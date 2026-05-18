"""
Git Webhook 配置数据模型模块

本模块定义了 Git Webhook 配置的数据模型，用于接收来自 Git 托管平台
（如 GitHub、GitLab、Gitea 等）的 Webhook 事件，实现代码变更自动同步。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class GitWebhookConfig(Base):
    """
    Git Webhook 配置数据模型
    
    配置 Git 仓库的 Webhook 接收设置，用于接收来自 Git 托管平台的事件通知，
    实现代码变更的自动同步和审计。
    
    属性:
        id: 配置记录唯一标识符（主键）
        repository_id: 关联的 Git 仓库 ID（外键）
        webhook_secret: Webhook 签名密钥（用于验证请求来源）
        provider: Git 托管平台（"github", "gitlab", "gitea", "bitbucket" 等）
        enabled: 是否启用 Webhook
        auto_pull: 收到推送事件时是否自动执行 git pull
        created_at: 配置创建时间
    
    关系:
        repository: 关联的 Git 仓库对象
    
    安全说明:
        - webhook_secret 用于验证 Webhook 请求的真实性，防止伪造请求
        - 建议使用强随机字符串作为密钥
    """
    __tablename__ = "git_webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("git_repositories.id"), nullable=False, index=True)
    webhook_secret = Column(String(100))
    provider = Column(String(20))
    enabled = Column(Boolean, default=True)
    auto_pull = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    repository = relationship("GitRepository", back_populates="webhook_config")