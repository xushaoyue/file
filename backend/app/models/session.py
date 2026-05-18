"""
会话数据模型模块

本模块定义了用户会话的数据模型，用于管理用户的登录会话状态，
包括访问令牌、刷新令牌、会话过期、撤销等功能。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class Session(Base):
    """
    会话数据模型
    
    管理用户的登录会话信息，存储访问令牌和刷新令牌的状态，
    支持会话撤销和强制登出功能。
    
    属性:
        id: 会话记录唯一标识符（主键）
        session_id: 会话唯一标识符（UUID）
        user_id: 所属用户的 ID（外键，级联删除）
        token_hash: 访问令牌的哈希值（用于验证和黑名单机制）
        refresh_token_hash: 刷新令牌的哈希值
        expires_at: 访问令牌过期时间
        refresh_expires_at: 刷新令牌过期时间
        created_at: 会话创建时间
        last_activity: 最后活动时间
        revoked_at: 会话撤销时间（如已撤销）
        is_active: 会话是否活跃
        ip_address: 客户端 IP 地址
        user_agent: 客户端 User-Agent 信息
    
    关系:
        user: 关联的用户对象
    
    安全说明:
        - 只存储令牌的哈希值，不存储原始令牌
        - 支持单独撤销某个会话或用户的所有会话
        - 令牌过期后自动失效
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True)
    refresh_token_hash = Column(String(255))
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime)
    revoked_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(50))
    user_agent = Column(Text)

    user = relationship("User", back_populates="sessions")
