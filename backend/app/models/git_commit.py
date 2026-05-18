from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from backend.app.database import Base


class GitCommit(Base):
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