"""
权限数据模型模块

本模块定义了用户权限的数据模型，用于细粒度控制用户对文件系统的访问权限，
包括读取、写入、删除、下载等操作的权限控制。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class Permission(Base):
    """
    权限数据模型
    
    定义用户对特定文件或目录路径的访问权限，实现基于路径的细粒度权限控制。
    支持对读取、写入、删除、下载等操作进行独立控制。
    
    属性:
        id: 权限记录唯一标识符（主键）
        user_id: 所属用户的 ID（外键，级联删除）
        allowed_path: 允许访问的文件或目录路径（支持前缀匹配）
        can_read: 是否允许读取操作
        can_write: 是否允许写入/修改操作
        can_delete: 是否允许删除操作
        can_download: 是否允许下载操作
        created_at: 权限创建时间
        updated_at: 权限最后更新时间
    
    关系:
        user: 关联的用户对象
    
    权限匹配说明:
        当用户访问某个路径时，系统会查找最具体匹配的权限规则。
        如果有多个规则匹配，最长路径的规则优先级最高。
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    allowed_path = Column(String(500), nullable=False, index=True)
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_download = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="permissions")
