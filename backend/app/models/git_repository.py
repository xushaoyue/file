"""
Git 仓库数据模型模块

本模块定义了 Git 仓库的数据模型，用于管理系统中的 Git 代码仓库，
支持远程仓库同步、分支管理、认证配置等功能。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class GitRepository(Base):
    """
    Git 仓库数据模型
    
    表示系统管理的一个 Git 代码仓库，包含仓库的基本信息、
    远程地址、本地路径、认证配置和同步状态。
    
    属性:
        id: 仓库唯一标识符（主键）
        name: 仓库名称（唯一）
        remote_url: Git 远程仓库 URL（HTTPS 或 SSH）
        local_path: 仓库在本地文件系统中的路径（唯一）
        branch: 默认跟踪的分支名称
        auth_type: 认证类型（"none", "password", "ssh_key", "token"）
        auth_credential: 认证凭据（加密存储）
        status: 仓库状态（"cloned", "syncing", "synced", "error"）
        last_synced_at: 最后一次同步时间
        created_at: 仓库添加时间
        updated_at: 仓库信息最后更新时间
    
    关系:
        commits: 该仓库的提交记录列表
        webhook_config: 关联的 Webhook 配置（一对一关系）
    """
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