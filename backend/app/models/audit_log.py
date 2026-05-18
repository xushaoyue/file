"""
审计日志数据模型模块

本模块定义了系统审计日志的数据模型，用于记录用户对文件的所有操作，
包括文件的创建、修改、删除、读取等，便于安全审计和问题追踪。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class AuditLog(Base):
    """
    审计日志数据模型
    
    记录系统中的每一个关键操作，包括文件操作、用户活动等，
    用于安全审计、问题追踪和合规检查。
    
    属性:
        id: 日志唯一标识符（主键）
        timestamp: 事件发生时间
        event_type: 事件类型（如 "FILE_MODIFIED", "USER_LOGIN", "PERMISSION_CHANGE" 等）
        user_id: 执行操作的用户 ID（外键，用户删除后设为 NULL）
        username: 执行操作的用户名（冗余字段，便于查询）
        user_role: 执行操作时用户的角色
        operation: 具体操作类型（如 "read", "write", "delete", "download", "list" 等）
        file_path: 操作涉及的文件或目录路径
        file_size_before: 操作前文件大小（字节）
        file_size_after: 操作后文件大小（字节）
        status: 操作状态（"success", "failure", "error"）
        client_ip: 客户端 IP 地址
        user_agent: 客户端 User-Agent 信息
        session_id: 会话 ID
        diff_content: 文件变更差异内容（如适用）
        error_message: 错误信息（如操作失败）
        extra_data: 额外的元数据（JSON 格式）
    
    关系:
        user: 关联的用户对象（如用户未删除）
    """
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
    extra_data = Column(JSON)

    user = relationship("User", back_populates="audit_logs")
