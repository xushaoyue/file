from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    operation: str
    file_path: str
    file_size_before: Optional[int] = None
    file_size_after: Optional[int] = None
    status: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    diff_content: Optional[str] = None
    error_message: Optional[str] = None
    extra_data: Optional[dict] = None

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    operation: Optional[str] = None
    file_path: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="timestamp")
    sort_order: str = Field(default="desc")


class AuditLogList(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditStats(BaseModel):
    total_operations: int
    operations_by_type: Dict[str, int]
    top_users: List[Dict[str, Any]]
    top_files: List[Dict[str, Any]]
