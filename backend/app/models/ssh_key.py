"""
SSH 密钥数据模型模块

本模块定义了用户 SSH 密钥的数据模型，用于支持 SSH 密钥认证方式，
允许用户通过 SSH 密钥访问系统而无需输入密码。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class SSHKey(Base):
    """
    SSH 密钥数据模型
    
    存储用户的 SSH 公钥信息，用于 SSH 密钥认证。支持多种密钥类型，
    如 RSA、ED25519、ECDSA 等。
    
    属性:
        id: 密钥唯一标识符（主键）
        user_id: 所属用户的 ID（外键，级联删除）
        key_name: 密钥的自定义名称（用于用户识别）
        public_key: SSH 公钥内容（完整字符串）
        key_type: 密钥类型（如 "ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256"）
        fingerprint: 密钥的指纹（用于快速验证）
        created_at: 密钥添加时间
        last_used: 密钥最后一次使用时间
        is_active: 密钥是否启用
    
    关系:
        user: 关联的用户对象
    """
    __tablename__ = "ssh_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_name = Column(String(100))
    public_key = Column(Text, nullable=False)
    key_type = Column(String(20))
    fingerprint = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="ssh_keys")
