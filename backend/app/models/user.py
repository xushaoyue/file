"""
用户数据模型模块

本模块定义了系统用户的数据模型，包含用户的基本信息、认证状态、
以及与其他模型的关系（SSH密钥、权限、审计日志、会话等）。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class User(Base):
    """
    用户数据模型
    
    表示系统中的一个用户，包含用户基本信息、认证状态和权限相关字段。
    
    属性:
        id: 用户唯一标识符（主键）
        username: 用户名（唯一，用于登录）
        password_hash: 加密后的用户密码（bcrypt哈希）
        full_name: 用户全名（可选）
        email: 用户邮箱（唯一，可选）
        role: 用户角色，如 "admin"（管理员）或 "user"（普通用户）
        is_active: 账户是否启用
        must_change_password: 首次登录是否必须修改密码
        created_at: 账户创建时间
        updated_at: 账户最后更新时间
        last_login: 最后登录时间
        failed_attempts: 连续登录失败次数（用于账户锁定）
        locked_until: 账户锁定截止时间（如被锁定）
    
    关系:
        ssh_keys: 该用户的 SSH 密钥列表
        permissions: 该用户的权限配置列表
        audit_logs: 该用户的操作审计日志
        sessions: 该用户的活跃会话列表
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    ssh_keys = relationship("SSHKey", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
