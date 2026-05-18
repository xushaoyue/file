"""
Git 提交记录数据模型模块

本模块定义了 Git 提交记录的数据模型，用于存储和追踪仓库的提交历史，
包括提交信息、作者、变更统计等，便于代码审计和版本追踪。
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from backend.app.database import Base


class GitCommit(Base):
    """
    Git 提交记录数据模型
    
    存储 Git 仓库的提交记录，包含提交信息、作者信息、变更统计等，
    用于代码审计、版本追踪和变更分析。
    
    属性:
        id: 提交记录唯一标识符（主键）
        repository_id: 所属仓库的 ID（外键）
        commit_hash: Git 提交哈希值（SHA-1，40字符）
        author_name: 作者姓名
        author_email: 作者邮箱
        committer_name: 提交者姓名
        committer_email: 提交者邮箱
        message: 提交信息（commit message）
        committed_at: 提交时间
        branch: 提交所在的分支
        parents: 父提交哈希（多个用逗号分隔）
        files_changed: 变更的文件数量
        insertions: 新增行数
        deletions: 删除行数
        audit_event_id: 关联的审计日志 ID（可选）
    
    关系:
        repository: 关联的 Git 仓库对象
    """
    __tablename__ = "git_commits"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("git_repositories.id"), nullable=False, index=True)
    commit_hash = Column(String(40), nullable=False, index=True)
    author_name = Column(String(100))
    author_email = Column(String(100))
    committer_name = Column(String(100))
    committer_email = Column(String(100))
    message = Column(String(1000))
    committed_at = Column(DateTime, index=True)
    branch = Column(String(100))
    parents = Column(String(200))
    files_changed = Column(Integer)
    insertions = Column(Integer)
    deletions = Column(Integer)
    audit_event_id = Column(Integer, ForeignKey("audit_logs.id"), nullable=True)

    repository = relationship("GitRepository", back_populates="commits")